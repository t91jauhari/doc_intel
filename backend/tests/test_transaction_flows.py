import copy
import pytest
from sqlalchemy import select
from app.db import Case, Config, SessionLocal
from app.domain import default_config, latest_config, validate_config
from app.transaction_flows import scope_configuration, seed_transaction_flows
from app.config_workbook import export_config, import_config
from test_platform import upload


def test_validation_blocks_bad_keys_duplicate_names_unknown_documents_and_rules():
    original = default_config()
    for key, flow in [('invalid key', {'label':'New','required':[]}), ('valid', {'label':'Flexible case','required':[]}), ('valid', {'label':'New','required':['not_a_profile']}), ('valid', {'label':'New','required':[],'sop_rule_ids':['unknown']})]:
        cfg = copy.deepcopy(original)
        cfg['templates'][key] = flow
        with pytest.raises(ValueError): validate_config(cfg)
    cfg = copy.deepcopy(original)
    for flow in cfg['templates'].values(): flow['enabled'] = False
    with pytest.raises(ValueError): validate_config(cfg)


def test_new_flow_scopes_rules_and_report_category_without_mutating_config():
    cfg = default_config()
    cfg['templates']['account_opening'] = {'label':'Account Opening','required':['ektp'],'sop_rule_ids':[]}
    scoped = scope_configuration(cfg, 'account_opening')
    assert scoped['sop_rules'] == []
    assert scoped['report_context']['category'] == 'Account Opening'
    assert cfg['sop_rules']
    assert scope_configuration(cfg, 'forex')['sop_rules'] == cfg['sop_rules']
    rule = cfg['sop_rules'][0]['id']
    cfg['templates']['account_opening']['sop_rule_ids'] = [rule]
    assert [r['id'] for r in scope_configuration(cfg, 'account_opening')['sop_rules']] == [rule]


def test_startup_seed_and_workbook_roundtrip(signed):
    cfg = signed.get('/api/config').json()['payload']
    assert len(cfg['templates']['account_opening']['sop_rule_ids']) == 206
    with SessionLocal() as db: version = latest_config(db, 'sqe').version
    seed_transaction_flows()
    with SessionLocal() as db: assert latest_config(db, 'sqe').version == version
    imported, errors = import_config(export_config(cfg), cfg)
    assert not errors, errors
    assert imported['templates'] == cfg['templates']


def test_create_archive_and_existing_case_pin(signed):
    current = signed.get('/api/config').json()
    current['payload']['templates']['new_service'] = {'label':'New service','enabled':True,'description':'Custom transaction flow','required':['ektp'],'sop_rule_ids':[]}
    result = signed.post('/api/config/publish', json={'expected_version':current['version'],'payload':current['payload']})
    assert result.status_code == 200, result.text
    first = upload(signed, names=('Customer_ektp.pdf',), key='new-flow', template='new_service')
    assert first.status_code == 202, first.text
    case_id = first.json()['case_ids'][0]
    with SessionLocal() as db: config_id = db.get(Case, case_id).config_id
    current = signed.get('/api/config').json()
    current['payload']['templates']['new_service']['enabled'] = False
    assert signed.post('/api/config/publish', json={'expected_version':current['version'],'payload':current['payload']}).status_code == 200
    blocked = upload(signed, names=('Other_ektp.pdf',), key='archived-flow', template='new_service')
    assert blocked.status_code == 422
    with SessionLocal() as db: assert db.get(Case, case_id).config_id == config_id
    assert signed.get(f'/api/cases/{case_id}').json()['transaction_flow_label'] == 'New service'
    filtered = signed.get('/api/cases?transaction_flow=new_service').json()
    assert filtered['total'] == 1 and filtered['items'][0]['id'] == case_id
    assert signed.get('/api/cases?transaction_flow=account_opening').json()['total'] == 0


def test_account_opening_processing_does_not_apply_forex_sop(signed):
    from test_platform import publish_fixture, process_all
    publish_fixture(signed)
    current = signed.get('/api/config').json()
    current['payload']['templates']['account_opening']['required'] = ['ektp', 'riplay']
    assert signed.post('/api/config/publish', json={'expected_version':current['version'],'payload':current['payload']}).status_code == 200
    response = upload(signed, names=('New Customer_ektp.pdf',), key='account-pack', template='account_opening')
    assert response.status_code == 202
    case_id = response.json()['case_ids'][0]
    process_all()
    result = signed.get(f'/api/cases/{case_id}').json()
    snapshot = result['reports'][0]['snapshot']
    assert snapshot['missing'] == ['riplay']
    assert snapshot['findings'] and all(f['rule_id'].startswith('AO_') for f in snapshot['findings'])
    from app.db import Report
    with SessionLocal() as db:
        saved = db.scalar(select(Report).where(Report.case_id == case_id).order_by(Report.version.desc()))
        assert saved.snapshot['configuration']['report_context']['category'] == 'Teller'
        assert saved.snapshot['transaction_flow']['id'] == 'account_opening'
    assert snapshot['validation_status'] == 'FAIL'  # Mandatory opening form is absent.


def test_attach_to_archived_flow_uses_pinned_case(signed):
    from test_platform import PDF
    first = upload(signed, names=('Customer_ektp.pdf',), key='before-archive', template='account_opening')
    case_id = first.json()['case_ids'][0]
    current = signed.get('/api/config').json()
    current['payload']['templates']['account_opening']['enabled'] = False
    assert signed.post('/api/config/publish', json={'expected_version':current['version'],'payload':current['payload']}).status_code == 200
    branch = signed.get('/api/branches').json()[0]['id']
    response = signed.post('/api/uploads', data={'branch_id':branch,'template':'account_opening','case_id':case_id}, files=[('files',('Customer_riplay.pdf',PDF,'application/pdf'))], headers={'Idempotency-Key':'attach-after-archive'})
    assert response.status_code == 202, response.text
