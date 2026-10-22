import copy
from sqlalchemy import select
from app.db import Config,Document,FieldReprocess,SessionLocal,User
from app.processor import process_job
from test_field_reprocessing import completed
from test_platform import upload


def test_guidance_publishes_only_target_profile_and_reaches_future_uploads(signed,monkeypatch):
    doc=completed(signed)
    before=signed.get('/api/config').json()
    seen=[]
    def extract(d,req,beat):
        seen.append(copy.deepcopy(req.payload))
        return {'name':{'raw':'Visible name','complete':True}}
    monkeypatch.setattr('app.field_reprocessing.extract_selected',extract)
    body={'fields':['name'],'reason':'Read printed name','instruction':'Read the printed name line.\n\nKeep separate from signatures.'}
    response=signed.post(f'/api/documents/{doc.id}/reprocess-fields',json=body)
    assert response.status_code==202,response.text
    receipt=response.json()
    assert receipt['guidance_saved_to_profile'] and receipt['guidance_appended']
    after=signed.get('/api/config').json()
    assert after['version']==before['version']+1==receipt['config_version']
    for name,p in before['payload']['profiles'].items():
        if name!='ektp':assert after['payload']['profiles'][name]==p
    prompt=after['payload']['profiles']['ektp']['system_instruction']
    assert 'Reusable extraction guidance (fields: name)' in prompt
    assert body['instruction'] in prompt
    process_job(receipt['job_id'])
    assert seen[0]['config']['profiles']['ektp']['system_instruction']==prompt
    assert seen[0]['guidance_saved_to_profile']
    history=signed.get(f'/api/documents/{doc.id}/reprocess-fields').json()
    assert history[0]['guidance_saved_to_profile'] is True
    assert history[0]['instruction']==body['instruction']
    # Exact repeated guidance, including paragraphs, is not appended/published twice.
    repeated=signed.post(f'/api/documents/{doc.id}/reprocess-fields',json=body)
    assert repeated.status_code==202,repeated.text
    assert repeated.json()['guidance_appended'] is False
    assert signed.get('/api/config').json()['version']==after['version']
    fresh=upload(signed,names=('Future Customer_ektp.pdf',),key='future-guidance')
    with SessionLocal() as db:
        from app.db import Case
        case=db.get(Case,fresh.json()['case_ids'][0])
        assert db.get(Config,case.config_id).payload['profiles']['ektp']['system_instruction']==prompt


def test_invalid_requests_do_not_publish_and_request_only_is_preserved(signed):
    doc=completed(signed);url=f'/api/documents/{doc.id}/reprocess-fields'
    before=signed.get('/api/config').json()
    assert signed.post(url,json={'fields':['missing'],'reason':'Inspect field','instruction':'Look at the complete line'}).status_code==422
    assert signed.post(url,json={'fields':['name'],'reason':'Inspect field','instruction':'Look at the complete line','use_latest_config':False}).status_code==422
    assert signed.get('/api/config').json()['version']==before['version']
    response=signed.post(url,json={'fields':['name'],'reason':'Inspect field','instruction':'This document only','save_to_profile':False,'use_latest_config':False})
    assert response.status_code==202,response.text
    assert not response.json()['guidance_saved_to_profile']
    assert signed.get('/api/config').json()['version']==before['version']
    with SessionLocal() as db:
        req=db.scalar(select(FieldReprocess).where(FieldReprocess.job_id==response.json()['job_id']))
        assert req.payload['instruction']=='This document only'
        assert not req.payload['guidance_saved_to_profile']


def test_shared_guidance_requires_config_publish_permission(signed):
    doc=completed(signed);before=signed.get('/api/config').json()['version']
    user=signed.get('/api/auth/session').json()['user']
    with SessionLocal.begin() as db:db.get(User,user['id']).role='officer'
    body={'fields':['name'],'reason':'Inspect name','instruction':'Read only the printed name box'}
    assert signed.post(f'/api/documents/{doc.id}/reprocess-fields',json=body).status_code==403
    with SessionLocal() as db:assert db.scalar(select(Config).order_by(Config.version.desc())).version==before
    body['save_to_profile']=False
    assert signed.post(f'/api/documents/{doc.id}/reprocess-fields',json=body).status_code==202


def test_profile_length_limit_rolls_back_publication(signed):
    doc=completed(signed)
    current=signed.get('/api/config').json()
    from app.extraction_prompts import system_instruction
    # Include the mandatory spatial instruction in the published length budget.
    compiled=system_instruction({'system_instruction':'x'})
    current['payload']['profiles']['ektp']['system_instruction']='x'*(29995-len(compiled)+1)
    saved=signed.post('/api/config/publish',json={'expected_version':current['version'],'payload':current['payload']})
    assert saved.status_code==200,saved.text
    response=signed.post(f'/api/documents/{doc.id}/reprocess-fields',json={'fields':['name'],'reason':'Inspect field','instruction':'Inspect the entire printed name line'})
    assert response.status_code==422,response.text
    assert signed.get('/api/config').json()['version']==saved.json()['version']
