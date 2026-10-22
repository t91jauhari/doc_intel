import copy,json
from types import SimpleNamespace
import httpx
import pytest
from app.db import SessionLocal,Document,Job
from app.provider import ProcessingIssue,state_of
from app.spider_failures import failure_details,confirmed_connection_rejection
from app.spider_provider import completion
from app.storage import store,object_key
from app.processor import process_job
from test_field_reprocessing import completed

BODY={'error':{'message':'[model-route] [502]: fetch connect timeout (reset after 30s)'}}


def pending_response(doc,stage,body=BODY,matching=True):
    key=object_key(doc.org,doc.branch_id,'documents',doc.id,'recovery-http-error.json')
    store().put(key,json.dumps(body).encode(),'application/json')
    return {'pending_create':'spider_'+stage,'provider_stage':'SPIDER_'+stage.upper(),
            'spider_request_id':'request-1','spider_http_response':{'stage':stage,'status':503,'body_key':key,'request_id':'request-1' if matching else 'older-request'}}


def test_only_explicit_preconnection_failure_is_safe():
    assert failure_details(503,BODY)['retry_safe']
    for body in [None,{'error':{'message':'read timeout after upstream submission'}},{'error':{'message':None}},{'message':'fetch connect timeout'}]:
        assert not failure_details(503,body)['retry_safe']
    assert not failure_details(500,BODY)['retry_safe']


def test_transport_records_connection_rejection_without_stranding_submission(signed,monkeypatch):
    doc=completed(signed);calls=[]
    class Client:
        def __init__(self,**kw):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,*args,**kwargs):
            calls.append(True)
            return httpx.Response(503,json=BODY) if len(calls)==1 else httpx.Response(200,json={'choices':[{'message':{'content':'{}'}}]})
    monkeypatch.setattr('app.spider_provider.httpx.Client',Client)
    with pytest.raises(ProcessingIssue,match='could not connect to the model'):
        completion(doc,'fields_recovery_1',[],{},'not-live',lambda:None)
    state=state_of(doc.id)
    assert state['pending_create'] is None
    assert state['spider_http_response']['failure']['retry_safe']
    completion(doc,'fields_recovery_1',[],{},'not-live',lambda:None)
    assert len(calls)==2


@pytest.mark.parametrize('matching,body,requires_ack',[(True,BODY,False),(False,BODY,True),(True,{'error':{'message':'upstream read timed out'}},True)])
def test_legacy_field_recovery_checks_saved_response_and_keeps_values(signed,monkeypatch,matching,body,requires_ack):
    doc=completed(signed);before=copy.deepcopy(doc.raw)
    request=signed.post(f'/api/documents/{doc.id}/reprocess-fields',json={'fields':['name'],'reason':'Inspect name'}).json()
    stage='fields_'+request['request_id']+'_1'
    with SessionLocal.begin() as db:
        stored=db.get(Document,doc.id);stored.status='COMPLETED';stored.error='Spider-AI HTTP 503.'
        stored.provider_state=pending_response(doc,stage,body,matching)
        job=db.get(Job,request['job_id']);job.status='ERROR';job.error=stored.error
    history=signed.get(f'/api/documents/{doc.id}/reprocess-fields').json()[0]
    assert history['can_retry'] and history['requires_duplicate_charge_ack']==requires_ack
    wrong=signed.post(f'/api/documents/{doc.id}/spider-resubmit',json={'reason':'Try recovery','accept_possible_duplicate_charge':True})
    assert wrong.status_code==409 and 'field' in wrong.text
    url=f"/api/documents/{doc.id}/reprocess-fields/{request['request_id']}/retry"
    resumed=signed.post(url)
    if requires_ack:
        assert resumed.status_code==409
        with SessionLocal() as db:assert db.get(Document,doc.id).raw==before and db.get(Document,doc.id).provider_state['pending_create']
        return
    assert resumed.status_code==202,resumed.text
    with SessionLocal() as db:assert db.get(Document,doc.id).raw==before and db.get(Document,doc.id).provider_state['pending_create'] is None
    monkeypatch.setattr('app.field_reprocessing.extract_selected',lambda *args:{'name':{'raw':'RECOVERED','complete':True}})
    process_job(resumed.json()['job_id'])
    with SessionLocal() as db:
        stored=db.get(Document,doc.id)
        assert stored.status=='COMPLETED' and not stored.error
        assert stored.normalized['name']=='RECOVERED'
        assert {k:v for k,v in stored.raw.items() if k!='name'}=={k:v for k,v in before.items() if k!='name'}


def test_legacy_full_document_connection_rejection_can_retry(signed):
    doc=completed(signed)
    with SessionLocal.begin() as db:
        stored=db.get(Document,doc.id);stored.status='ERROR';stored.raw={}
        stored.provider_state=pending_response(doc,'extract')
    response=signed.post(f'/api/documents/{doc.id}/retry')
    assert response.status_code==202,response.text
    with SessionLocal() as db:assert db.get(Document,doc.id).provider_state['pending_create'] is None
