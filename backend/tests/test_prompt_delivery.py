"""Assert prompt delivery at the outbound HTTP/SDK boundary, without paid calls."""
import copy,json
from types import SimpleNamespace
import httpx
import pytest
from app.db import Document,SessionLocal
from app.domain import default_config
from app.provider import run_provider,fixture_response,ProcessingIssue,state_of
from app.field_reprocessing import extract_selected,selected_schema
from app.extraction_prompts import prompt_manifest
from test_spider_provider import create_case,save_key


def configured(signed,provider='spider-ai'):
    doc=create_case(signed)
    doc.classification={'manual':True,'type':'application','confirmed':True}
    with SessionLocal.begin() as db:db.get(Document,doc.id).classification=doc.classification
    cfg=default_config();cfg['provider']=provider
    p=cfg['profiles']['application']
    p['system_instruction']='SYSTEM_SENTINEL: read original observations faithfully.'
    p['parse_prompt']='PARSER_SENTINEL: preserve layout and continuation lines.'
    p['system_prompt']='EXTRACTION_SENTINEL: use the saved field roles.'
    p['schema']['description']='ROOT_SENTINEL: application fields.'
    p['schema']['properties']['branch']['description']='FIELD_SENTINEL: entered branch only.'
    p['schema']['properties']['beneficiary']['properties']['name']['description']='CHILD_SENTINEL: distinct recipient name.'
    p['schema']['properties']['payment_type']['properties']['options']['items']['properties']['label']['description']='ARRAY_CHILD_SENTINEL: printed option label.'
    p['schema']['properties']['swift_code']['description']='UNSELECTED_SENTINEL'
    return doc,cfg,p


@pytest.mark.parametrize('sequential',[False,True])
def test_spider_every_extraction_request_delivers_all_active_prompts(signed,monkeypatch,sequential):
    doc,cfg,p=configured(signed);save_key(signed)
    cfg['sequential_page_extraction']=sequential
    calls=[]
    class Client:
        def __init__(self,**kw):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,url,headers,json):
            calls.append(copy.deepcopy(json))
            return httpx.Response(200,json={'id':'wire-'+str(len(calls)), 'choices':[{'finish_reason':'stop','message':{'content':__import__('json').dumps(fixture_response('application')['extract_result'])}}]})
    monkeypatch.setattr('app.spider_provider.httpx.Client',Client)
    response,_=run_provider(doc,cfg,lambda:None)
    assert len(calls)==(2 if sequential else 1)
    for body in calls:
        wire=json.dumps(body['messages'])
        for sentinel in ['SYSTEM_SENTINEL','PARSER_SENTINEL','EXTRACTION_SENTINEL','ROOT_SENTINEL','FIELD_SENTINEL','CHILD_SENTINEL','ARRAY_CHILD_SENTINEL']:
            assert sentinel in wire
        assert '_prompt_manifest' not in body
    receipts=response['extract_metadata']['prompt_usage']
    assert all(r['status']=='RECORDED' and len(r['request_sha256'])==64 for r in receipts)
    assert all(r['manifest']==prompt_manifest(p,p['schema']) for r in receipts)
    again,_=run_provider(doc,cfg,lambda:None)
    assert again==response and len(calls)==(2 if sequential else 1)
    p['parse_prompt']+=' Changed after the saved provider response.'
    with pytest.raises(ProcessingIssue,match='different profile prompts'):
        run_provider(doc,cfg,lambda:None)
    assert len(calls)==(2 if sequential else 1)


@pytest.mark.parametrize('saved_guidance',[False,True])
def test_selected_spider_delivers_all_prompts_and_only_selected_field_descriptions(signed,monkeypatch,saved_guidance):
    doc,cfg,p=configured(signed);save_key(signed);calls=[]
    request=SimpleNamespace(id='wire-fields',payload={'config':cfg,'fields':['branch','beneficiary'],'instruction':'REVIEWER_SENTINEL: inspect both lines.'})
    if saved_guidance:
        p['system_instruction']+='\nReusable extraction guidance (fields: beneficiary, branch):\n'+request.payload['instruction']
        request.payload['guidance_saved_to_profile']=True
    class Client:
        def __init__(self,**kw):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,url,headers,json):
            calls.append(copy.deepcopy(json))
            return httpx.Response(200,json={'id':'selected','choices':[{'message':{'content':'{"branch":"Jakarta","beneficiary":{"name":"Recipient"}}'}}]})
    monkeypatch.setattr('app.spider_provider.httpx.Client',Client)
    assert extract_selected(doc,request,lambda:None)['branch']=='Jakarta'
    assert len(calls)==2
    for body in calls:
        wire=json.dumps(body['messages'])
        for sentinel in ['SYSTEM_SENTINEL','PARSER_SENTINEL','EXTRACTION_SENTINEL','ROOT_SENTINEL','FIELD_SENTINEL','CHILD_SENTINEL','REVIEWER_SENTINEL']:
            assert sentinel in wire
        assert 'UNSELECTED_SENTINEL' not in wire
        assert 'ARRAY_CHILD_SENTINEL' not in wire
    state=state_of(doc.id)
    assert set(state['spider_fields_wire-fields_1_prompt_manifest']['fields'])=={'branch','beneficiary'}
    extract_selected(doc,request,lambda:None)
    assert len(calls)==2






def test_location_guidance_is_scoped_to_selected_fields_and_frozen_for_retries(signed,monkeypatch):
    from app.extraction_prompts import saved_location_guidance
    doc,cfg,p=configured(signed)
    hints=[{'field':f,'page_number':1,'bbox':[.1,.2,.5,.3],'units':'normalized','sample_ids':['private-example-id']}
           for f in ['branch','swift_code']]
    calls=[]
    def retrieve(*args):calls.append(True);return hints
    monkeypatch.setattr('app.location_learning.retrieve',retrieve)
    selected,text=saved_location_guidance(doc,p,'field_location_guidance_test',['branch'])
    assert [h['field'] for h in selected]==['branch']
    assert 'branch' in text and 'swift_code' not in text and 'private-example-id' not in text
    hints.clear()
    assert saved_location_guidance(doc,p,'field_location_guidance_test',['branch'])==(selected,text)
    assert len(calls)==1
