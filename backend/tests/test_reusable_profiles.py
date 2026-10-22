import copy,json
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from app.domain import default_config,validate_config
from app.extraction_quality import apply_quality
from app.profile_context import apply_context

def context(before='JL. KEMENDANGAN MERDEKA NO. 101',sources=None,overrides=None):
    cfg=apply_quality(default_config())
    doc=SimpleNamespace(id='target',case_id='case',org='org',branch_id='branch',doc_type='valas_declaration_1',overrides=overrides or {})
    db=Mock();db.scalars.return_value=sources if sources is not None else [SimpleNamespace(id='source',overrides={},normalized={'payer_address':{'raw':'JL. KEMENANGAN MERDEKA NO. 101'}})]
    report={'normalized':{'customer_address':{'raw':before,'complete':True}},'original_raw':{'customer_address':{'raw':before,'complete':True}},'fields':{'customer_address':{}},'corrections':[]}
    return db,doc,cfg,report

def test_config_instructions_and_controls_are_reusable_and_validated():
    cfg=apply_quality(default_config());validate_config(cfg)
    assert apply_quality(cfg)==cfg
    assert cfg['profiles']['lld']['policy']['extraction_sampling']['temperature']==0
    assert len(cfg['profiles']['lld']['policy']['extraction_detail_regions'])==3
    assert 'lowercase l' in cfg['profiles']['lld']['schema']['properties']['beneficiary_address']['description']
    assert '[Published extraction rules]' in cfg['profiles']['lld']['system_instruction']
    for invalid in [-1,3,float('nan')]:
        bad=copy.deepcopy(cfg);bad['profiles']['lld']['policy']['extraction_sampling']['temperature']=invalid
        with pytest.raises(ValueError):validate_config(bad)
    bad=copy.deepcopy(cfg);bad['profiles']['lld']['policy']['extraction_detail_regions'][0]['box']=[0,0,2,1]
    with pytest.raises(ValueError):validate_config(bad)

def test_context_is_automatic_scoped_traceable_and_not_a_reviewer_override():
    db,doc,cfg,report=context();raw=copy.deepcopy(report['original_raw'])
    result=apply_context(db,doc,cfg,report)
    assert result['normalized']['customer_address']['raw']=='JL. KEMENANGAN MERDEKA NO. 101'
    assert result['original_raw']==raw and doc.overrides=={}
    assert result['automatic_context']['source_document_id']=='source'
    params=db.scalars.call_args.args[0].compile().params
    assert {'case','org','branch','lld','COMPLETED','target'}<=set(params.values())

def test_context_rejects_different_numbers_conflicts_and_reviewed_sources():
    db,doc,cfg,report=context(before='JL. KEMENDANGAN MERDEKA NO. 102')
    assert 'automatic_context' not in apply_context(db,doc,cfg,report)
    db,doc,cfg,report=context(before='JL. KEMENDANGAN MERDEKA NO. 101B')
    assert 'automatic_context' not in apply_context(db,doc,cfg,report)
    source=SimpleNamespace(id='source',overrides={'payer_address':{}},normalized={'payer_address':{'raw':'JL. KEMENANGAN MERDEKA NO. 101'}})
    db,doc,cfg,report=context(sources=[source]);assert 'automatic_context' not in apply_context(db,doc,cfg,report)
    db,doc,cfg,report=context(overrides={'customer_address':{'raw':'Reviewed'}})
    assert 'automatic_context' not in apply_context(db,doc,cfg,report)
    db,doc,cfg,report=context(overrides={'customer_address':{'raw':'Reviewed'}})
    assert apply_context(db,doc,cfg,report,effective_overrides={})['automatic_context']['status']=='APPLIED'
    db,doc,cfg,report=context()
    assert 'automatic_context' not in apply_context(db,doc,cfg,report,selected={'customer_name'})
    sources=[SimpleNamespace(id=str(i),overrides={},normalized={'payer_address':{'raw':v}}) for i,v in enumerate(['JL. KEMENANGAN MERDEKA NO. 101','JL. KEMENANGGAN MERDEKA NO. 101'])]
    db,doc,cfg,report=context(sources=sources);before=copy.deepcopy(report['normalized'])
    result=apply_context(db,doc,cfg,report)
    assert result['automatic_context']['status']=='CONFLICT' and result['normalized']==before

def test_normal_extraction_sends_profile_sampling_and_detail_views(signed,monkeypatch):
    from test_spider_provider import create_case,save_key
    from app import spider_provider
    from app.provider import fixture_response,run_provider
    save_key(signed);doc=create_case(signed)
    doc.classification={'manual':True,'type':'application','confirmed':True}
    cfg=apply_quality(default_config());cfg['provider']='spider-ai';cfg['sequential_page_extraction']=False
    calls=[]
    def completion(d,stage,messages,options,key,heartbeat):
        calls.append((stage,messages,options))
        return {'id':'fresh','choices':[{'message':{'content':json.dumps(fixture_response('application')['extract_result'])}}]}
    monkeypatch.setattr(spider_provider,'completion',completion)
    response,_=run_provider(doc,cfg,lambda:None)
    assert response['extract_result']
    stage,messages,options=calls[0]
    assert stage=='extract' and options['temperature']==0 and options['top_p']==1
    assert '[Published extraction rules]' in messages[0]['content']
    content=messages[1]['content']
    assert sum(part['type']=='image_url' for part in content)==6 # 2 originals and 2 configured details per page
    assert any('Enlarged detail from the SAME original physical page' in p.get('text','') for p in content)
    assert 'entire recipient' in content[0]['text']
