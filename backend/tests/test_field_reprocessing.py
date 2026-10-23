import copy
import pytest
from sqlalchemy import select
from app.db import Case,Config,Document,FieldReprocess,Job,SessionLocal,User
from app.domain import default_config,validate_config,latest_config
from app.processor import process_job
from app.extraction_quality import apply_quality,INVOICE_FIELDS
from test_platform import upload,process_all,publish_fixture


def completed(signed):
    publish_fixture(signed)
    response=upload(signed,names=('Test Customer_ektp.pdf',),key='field-reprocess')
    process_all()
    with SessionLocal() as db:
        return db.scalar(select(Document).where(Document.case_id==response.json()['case_ids'][0]))


def test_added_schema_fields_and_provider_contracts():
    cfg=apply_quality(default_config())
    validate_config(cfg)
    assert set(INVOICE_FIELDS)<=set(cfg['profiles']['invoice']['schema']['properties'])
    assert 'stamp_verification' in dict(cfg['profiles']['valas_declaration_1']['columns'])
    schema=cfg['profiles']['ektp']['schema']
    schema['properties']['name']={'type':['string','null'],'description':'Printed name'}
    validate_config(cfg)
    cfg['provider']='fixture'
    with pytest.raises(ValueError,match='Native'):validate_config(cfg)
    cfg=apply_quality(default_config());cfg['provider']='fixture';validate_config(cfg)


def test_reprocess_preserves_other_fields_and_has_history(signed,monkeypatch):
    doc=completed(signed)
    before=copy.deepcopy(doc.raw)
    old_normal=copy.deepcopy(doc.normalized)
    current=signed.get('/api/config').json()
    cfg=current['payload']
    cfg['profiles']['ektp']['schema']['properties']['name']['description']='Latest field instruction used for re-extraction'
    assert signed.post('/api/config/publish',json={'expected_version':current['version'],'payload':cfg}).status_code==200
    seen=[]
    def extract(d,req,beat):
        seen.append(req.payload)
        return {'name':{'raw':'NEW PRINTED NAME','complete':True}}
    monkeypatch.setattr('app.field_reprocessing.extract_selected',extract)
    result=signed.post(f'/api/documents/{doc.id}/reprocess-fields',json={'fields':['name'],'reason':'Reinspect name','instruction':'Check complete line'})
    assert result.status_code==202,result.text
    assert signed.post(f'/api/documents/{doc.id}/reprocess-fields',json={'fields':['name'],'reason':'Duplicate request'}).status_code==409
    process_job(result.json()['job_id'])
    with SessionLocal() as db:
        updated=db.get(Document,doc.id)
        assert updated.status=='COMPLETED',updated.error
        assert updated.raw['name']['raw']=='NEW PRINTED NAME'
        assert {k:v for k,v in updated.raw.items() if k!='name'}=={k:v for k,v in before.items() if k!='name'}
        assert all(updated.normalized[k]==v for k,v in old_normal.items() if k!='name')
        assert db.get(Job,result.json()['job_id']).status=='COMPLETED'
    assert seen[0]['config']['profiles']['ektp']['schema']['properties']['name']['description'].startswith('Latest field')
    history=signed.get(f'/api/documents/{doc.id}/reprocess-fields').json()
    assert history[0]['result']['before']=={'name':before['name']}
    process_job(result.json()['job_id'])
    assert len(seen)==1


def test_reject_unknown_field_and_manual_override_and_unauthorized(signed):
    doc=completed(signed)
    url=f'/api/documents/{doc.id}/reprocess-fields'
    assert signed.post(url,json={'fields':['not_a_field'],'reason':'Try invalid'}).status_code==422
    with SessionLocal.begin() as db:db.get(Document,doc.id).overrides={'name':'Reviewed'}
    assert signed.post(url,json={'fields':['name'],'reason':'Try reviewed'}).status_code==409
    user=signed.get('/api/auth/session').json()['user']
    with SessionLocal.begin() as db:db.get(User,user['id']).role='officer'
    assert signed.post(url,json={'fields':['name'],'reason':'Try replacing review','replace_overrides':True}).status_code==403
    with SessionLocal.begin() as db:db.get(User,user['id']).role='auditor'
    assert signed.post(url,json={'fields':['nik'],'reason':'Try restricted'}).status_code==403


def test_bad_provider_patch_retains_original(signed,monkeypatch):
    doc=completed(signed)
    original=copy.deepcopy(doc.raw)
    monkeypatch.setattr('app.field_reprocessing.extract_selected',lambda *args:{'name':None,'nik':'unrequested'})
    response=signed.post(f'/api/documents/{doc.id}/reprocess-fields',json={'fields':['name'],'reason':'Inspect name'})
    process_job(response.json()['job_id'])
    with SessionLocal() as db:
        assert db.get(Document,doc.id).raw==original
        assert db.get(Document,doc.id).status=='COMPLETED'
        assert db.get(Job,response.json()['job_id']).status=='ERROR'


def test_all_validation_targets_get_guidance():
    import json
    from pathlib import Path
    from app.extraction_quality import COMMON
    targets=json.loads((Path(__file__).parents[1]/'app/config_data/validation_targets.json').read_text())
    config=apply_quality(default_config())
    assert len(targets)==49
    from app.reviewer_quality import RULES
    for t in targets:
        description=config['profiles'][t['profile']]['schema']['properties'][t['field']]['description']
        specific=RULES.get(t['profile'],{}).get(t['field'])
        assert (specific in description) if specific else (COMMON in description)
    assert apply_quality(config)==config


def test_resume_reuses_saved_paid_patch(signed,monkeypatch):
    doc=completed(signed)
    calls=[]
    def extract(*args):
        calls.append(True)
        return {'name':{'raw':'Observed Name','complete':True}}
    monkeypatch.setattr('app.field_reprocessing.extract_selected',extract)
    from app.provider import validate_extraction
    def fail(*args):raise ValueError('Simulated local validation interruption')
    monkeypatch.setattr('app.field_reprocessing.validate_extraction',fail)
    receipt=signed.post(f'/api/documents/{doc.id}/reprocess-fields',json={'fields':['name'],'reason':'Inspect name'}).json()
    process_job(receipt['job_id'])
    monkeypatch.setattr('app.field_reprocessing.validate_extraction',validate_extraction)
    resumed=signed.post(f"/api/documents/{doc.id}/reprocess-fields/{receipt['request_id']}/retry")
    assert resumed.status_code==202,resumed.text
    assert resumed.json()['job_id']!=receipt['job_id']
    process_job(resumed.json()['job_id'])
    with SessionLocal() as db:assert db.get(Job,resumed.json()['job_id']).status=='COMPLETED'
    assert len(calls)==1


def test_added_native_field_survives_validation(signed,monkeypatch):
    doc=completed(signed)
    cfg=signed.get('/api/config').json()
    profile=cfg['payload']['profiles']['ektp']
    profile['schema']['properties']['additional_note']={'type':['string','null'],'description':'Read additional note only.'}
    profile['columns'].append(['additional_note','Additional note'])
    saved=signed.post('/api/config/publish',json={'expected_version':cfg['version'],'payload':cfg['payload']})
    assert saved.status_code==200,saved.text
    monkeypatch.setattr('app.field_reprocessing.extract_selected',lambda *args:{'additional_note':'Visible note'})
    receipt=signed.post(f'/api/documents/{doc.id}/reprocess-fields',json={'fields':['additional_note'],'reason':'Extract new profile field'})
    assert receipt.status_code==202,receipt.text
    process_job(receipt.json()['job_id'])
    with SessionLocal() as db:
        updated=db.get(Document,doc.id)
        assert updated.normalized.get('additional_note')=='Visible note',updated.error


def test_selected_schema_is_limited_and_preserves_nested_guidance():
    from app.field_reprocessing import selected_schema
    profile=default_config()['profiles']['ektp']
    narrowed=selected_schema(profile,['nik'])
    assert set(narrowed['properties'])=={'nik'}
    assert narrowed['required']==['nik']
    assert narrowed['properties']['nik']==profile['schema']['properties']['nik']
    assert len(profile['schema']['properties'])>1
    from app.spider_provider import field_types
    assert field_types(narrowed)['nik']==['string','null']
    assert field_types(profile['schema'])['name.raw']==['string','null']
    from app.value_display import display_value
    assert display_value({'currency_raw':'USD','amount_raw':'1350','unit_raw':'MT'})=='USD 1350/MT'
    assert display_value({'table_complete':True,'items':[{'row_id':'1','raw':'Widget X1','complete':True}]})=='Widget X1'
    assert 'model/product-code column' in apply_quality(default_config())['profiles']['invoice']['schema']['properties']['item_name']['description']


def test_explicit_override_replacement_is_audited(signed,monkeypatch):
    doc=completed(signed)
    with SessionLocal.begin() as db:db.get(Document,doc.id).overrides={'name':{'raw':'Reviewer name','complete':True}}
    monkeypatch.setattr('app.field_reprocessing.extract_selected',lambda *args:{'name':{'raw':'Visible name','complete':True}})
    response=signed.post(f'/api/documents/{doc.id}/reprocess-fields',json={'fields':['name'],'reason':'Read name again','replace_overrides':True})
    assert response.status_code==202,response.text
    process_job(response.json()['job_id'])
    with SessionLocal() as db:
        updated=db.get(Document,doc.id)
        assert 'name' not in updated.overrides,updated.error
        assert updated.normalized['name']=='Visible name'
        req=db.scalar(select(FieldReprocess).where(FieldReprocess.job_id==response.json()['job_id']))
        assert req.result['previous_overrides']['name']['raw']=='Reviewer name'


def test_uncertain_field_retry_requires_explicit_ack(signed):
    doc=completed(signed)
    receipt=signed.post(f'/api/documents/{doc.id}/reprocess-fields',json={'fields':['name'],'reason':'Inspect name'}).json()
    with SessionLocal.begin() as db:
        db.get(Job,receipt['job_id']).status='ERROR'
        stored=db.get(Document,doc.id);stored.status='COMPLETED'
        stored.provider_state={'pending_create':'spider_fields_'+receipt['request_id']+'_1'}
    url=f"/api/documents/{doc.id}/reprocess-fields/{receipt['request_id']}/retry"
    assert signed.post(url).status_code==409
    assert signed.post(url,json={'accept_possible_duplicate_charge':True}).status_code==202
    with SessionLocal() as db:assert db.get(Document,doc.id).provider_state['pending_create'] is None




def test_cached_result_cannot_overwrite_newer_review(signed,monkeypatch):
    doc=completed(signed);calls=[]
    def extract(*args):calls.append(True);return {'name':{'raw':'Old provider reading','complete':True}}
    monkeypatch.setattr('app.field_reprocessing.extract_selected',extract)
    monkeypatch.setattr('app.field_reprocessing.validate_extraction',lambda *args:(_ for _ in ()).throw(ValueError('Local validation interruption')))
    receipt=signed.post(f'/api/documents/{doc.id}/reprocess-fields',json={'fields':['name'],'reason':'Inspect name'}).json()
    process_job(receipt['job_id'])
    with SessionLocal.begin() as db:
        db.get(Document,doc.id).overrides={'name':{'raw':'Newer reviewer decision','complete':True}}
    resumed=signed.post(f"/api/documents/{doc.id}/reprocess-fields/{receipt['request_id']}/retry")
    assert resumed.status_code==202,resumed.text
    process_job(resumed.json()['job_id'])
    with SessionLocal() as db:
        assert db.get(Job,resumed.json()['job_id']).status=='ERROR'
        assert 'changed after' in db.get(Job,resumed.json()['job_id']).error
        assert db.get(Document,doc.id).overrides['name']['raw']=='Newer reviewer decision'
    assert len(calls)==1
