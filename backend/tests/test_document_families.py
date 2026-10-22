import copy
import pytest
from sqlalchemy import select
from app.db import Case,Config,Document,SessionLocal
from app.domain import default_config,validate_config
from app.document_families import families,extraction_config
from app.transaction_flows import scope_configuration
from app.config_workbook import export_config,import_config
from test_platform import upload,publish_fixture,process_all

def configured(cfg):
    cfg=copy.deepcopy(cfg)
    cfg['document_families']={'loans':{'label':'Loan Applications','profiles':['ektp','riplay'],'required':['ektp'],
        'sop_rule_ids':[],'dataset_id':None,'report_layout':'forex','extraction_guidance':'Read every continuation line in this family.',
        'sequential_page_extraction':True,'report_context':{'activity':'Loan review'}}}
    cfg['templates']['loans']={'label':'Loan review','document_family':'loans','required':['ektp'],'sop_rule_ids':None,'dataset_id':None,'report_layout':'forex'}
    return cfg

def test_family_scope_and_defaults_are_non_mutating():
    cfg=configured(default_config());validate_config(cfg)
    original=copy.deepcopy(cfg)
    effective=extraction_config(cfg,'loans')
    assert effective['sequential_page_extraction'] is True
    assert 'Read every continuation line' in effective['profiles']['ektp']['system_instruction']
    assert effective['profiles']['invoice']==cfg['profiles']['invoice']
    assert extraction_config(cfg,'forex')==cfg
    assert cfg==original
    scoped=scope_configuration(cfg,'loans')
    assert scoped['sop_rules']==[]
    assert scoped['report_context']['activity']=='Loan review'
    assert set(families(cfg))=={'forex','account_opening','loans'}

@pytest.mark.parametrize('patch',[
 {'label':'Forex'}, {'profiles':[]}, {'profiles':['unknown']}, {'required':['invoice']},
 {'sop_rule_ids':['not-a-rule']},{'dataset_id':'invalid dataset id'},{'cross_page_reference':'yes'},
])
def test_bad_family_configuration_is_rejected(patch):
    cfg=configured(default_config());cfg['document_families']['loans'].update(patch)
    with pytest.raises(ValueError):validate_config(cfg)

def test_family_workbook_roundtrip():
    cfg=configured(default_config())
    result,errors=import_config(export_config(cfg),cfg)
    assert not errors,errors
    assert result['document_families']==cfg['document_families']
    assert result['templates']['loans']['dataset_id'] is None
    # Several long instructions must not be concatenated into one Excel cell.
    for i in range(5):
        cfg['document_families']['family_'+str(i)]={**cfg['document_families']['loans'],'label':'Family '+str(i),'extraction_guidance':'x'*9000}
    result,errors=import_config(export_config(cfg),cfg)
    assert not errors,errors
    assert result['document_families']==cfg['document_families']

def test_family_processing_and_archival_preserve_existing_cases(signed,monkeypatch):
    publish_fixture(signed)
    current=signed.get('/api/config').json();cfg=configured(current['payload'])
    response=signed.post('/api/config/publish',json={'expected_version':current['version'],'payload':cfg})
    assert response.status_code==200,response.text
    created=upload(signed,names=('Loan Customer_ektp.pdf',),key='family-case',template='loans')
    assert created.status_code==202,created.text
    from app import processor
    original=processor.run_provider;seen=[]
    def provider(doc,payload,beat):
        seen.append(copy.deepcopy(payload));return original(doc,payload,beat)
    monkeypatch.setattr(processor,'run_provider',provider)
    process_all()
    assert seen and 'Read every continuation line' in seen[0]['profiles']['ektp']['system_instruction']
    case_id=created.json()['case_ids'][0]
    with SessionLocal() as db:
        pinned=db.get(Case,case_id).config_id
        doc=db.scalar(select(Document).where(Document.case_id==case_id))
        assert doc.status=='COMPLETED',doc.error
        doc_id=doc.id
    latest=signed.get('/api/config').json();latest['payload']['document_families']['loans']['enabled']=False
    assert signed.post('/api/config/publish',json={'expected_version':latest['version'],'payload':latest['payload']}).status_code==200
    assert upload(signed,names=('Other Customer_ektp.pdf',),key='disabled-family',template='loans').status_code==422
    with SessionLocal() as db:assert db.get(Case,case_id).config_id==pinned
    # Existing documents can still be reread using their pinned configuration.
    rerun=signed.post(f'/api/documents/{doc_id}/reprocess-fields',json={'fields':['nik'],'reason':'Inspect original','use_latest_config':False})
    assert rerun.status_code==202,rerun.text
    from app.processor import process_job
    process_job(rerun.json()['job_id'])
    with SessionLocal() as db:assert db.get(Document,doc_id).status=='COMPLETED'
