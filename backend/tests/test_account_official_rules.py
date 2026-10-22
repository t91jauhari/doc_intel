import copy
import json
from pathlib import Path

import pytest
from sqlalchemy import select

from app.account_opening_official import RELEASE, seed_official_account_rules
from app.account_opening_sop import evaluate_rule
from app.db import Case, Config, Document, SessionLocal
from app.domain import default_config, latest_config, validate_config, refresh_case
from app.sop_scoring import normalize_findings
from test_account_opening import doc
from test_platform import publish_fixture, upload, process_all

RULES = json.loads((Path(__file__).parents[1] / "app/config_data/account_opening_rules.json").read_text(encoding="utf-8"))


def run(number, documents):
    rule = next(r for r in RULES if r['id'] == f'AO_SYSTEM_{number}')
    finding = evaluate_rule(rule, documents, default_config(), {})
    return normalize_findings([finding], [rule])[0]


def test_confirmed_package_excludes_external_specimens_but_keeps_cif_comparison():
    assert {int(r['id'].split('_')[-1]) for r in RULES if r['id'].startswith('AO_SYSTEM_')} == set(range(1, 16)) - {12}
    assert run(8, [doc('join_visit', cif='000123'), doc('account_opening_form', cif='000123')])['result'] == 'PASS'
    assert run(8, [doc('join_visit', cif='000123'), doc('account_opening_form', cif='123')])['result'] == 'FAIL'


@pytest.mark.parametrize('nik,expected', [('0123456789012345','PASS'),('123456789012345','FAIL'),('01234567890123456','FAIL'),('012345678901234X','FAIL')])
def test_same_invalid_nik_cannot_pass(nik, expected):
    assert run(1, [doc('ektp', nik=nik), doc('account_opening_form', identity_number=nik)])['result'] == expected


def test_only_supported_name_initials_can_enter_signature_review():
    ktp=doc('ektp', name='Artha Milani', owner_signature={'present': True})
    form=doc('account_opening_form', customer_name='Artha M.', customer_signature={'present': True})
    candidate=run(2, [ktp, form])
    assert candidate['result'] == 'REVIEW' and candidate['evaluation_type'] == 'VISUAL'
    assert candidate['evidence']['supporting_paths'] == ['ektp.owner_signature','account_opening_form.customer_signature']
    assert set(candidate['evidence']['document_ids'] + candidate['evidence']['reference_document_ids']) == {'ektp','account_opening_form'}
    # Mere signature presence is not a recorded consistency decision.
    assert candidate['result'] != 'PASS'
    for other in ('A. M.', 'Artha Mil.'):
        form['normalized']['customer_name']=other
        assert run(2,[ktp,form])['result']=='REVIEW'
    for other in ('Different Milani', 'Artha Milano', 'Milani Artha', 'Artha'):
        form['normalized']['customer_name']=other
        result=run(2,[ktp,form])
        assert result['result']=='FAIL' and result['evaluation_type']=='DATA'
    form['normalized']['customer_name']='ARTHA MILANI'
    assert run(2,[ktp,form])['result']=='PASS'


@pytest.mark.parametrize('combined', ['Jakarta / 27-10-1988','JAKARTA, 27 Oktober 1988','Jakarta,1988-10-27'])
def test_birth_place_and_date_support_real_form_delimiters(combined):
    assert run(3,[doc('ektp',birth_place='Jakarta',birth_date='27-10-1988'),doc('account_opening_form',birth_place_date=combined)])['result']=='PASS'


@pytest.mark.parametrize('combined', ['Bandung, 27-10-1988','Jakarta / 10-11-1988','Jakarta, Oktober 1988','27-10-1988','Jakarta'])
def test_birth_does_not_infer_or_accept_partial_components(combined):
    assert run(3,[doc('ektp',birth_place='Jakarta',birth_date='27-10-1988'),doc('account_opening_form',birth_place_date=combined)])['result']=='FAIL'


def test_gender_citizenship_and_occupation_follow_confirmed_rules():
    assert run(5,[doc('ektp',gender='PEREMPUAN'),doc('account_opening_form',gender='Wanita')])['result']=='PASS'
    assert run(5,[doc('ektp',gender='Laki-laki'),doc('account_opening_form',gender='Pria')])['result']=='PASS'
    assert run(5,[doc('ektp',gender='Perempuan'),doc('account_opening_form',gender='Pria')])['result']=='FAIL'
    for value, expected in [('WNI','PASS'),('WNA','PASS'),('Unknown','FAIL')]:
        assert run(6,[doc('ektp',citizenship=value),doc('account_opening_form',citizenship=value)])['result']==expected
    assert run(7,[doc('ektp',occupation='DOSEN'),doc('account_opening_form',occupation='Dosen')])['result']=='PASS'
    assert run(7,[doc('ektp',occupation='DOSEN'),doc('account_opening_form',occupation='Pegawai Swasta')])['result']=='FAIL'


def test_edd_company_comparison_includes_the_customers_job_title():
    edd=doc('edd',customer_name='Example Person',occupation='Account Executive')
    letter=doc('company_reference',customer_name='Example Person',customer_position='Account Executive',signatory_position='HR Manager')
    assert run(10,[edd,letter])['result']=='PASS'
    letter['normalized']['customer_position']='Manager'
    letter['normalized']['signatory_position']='Account Executive'
    failed=run(10,[edd,letter])
    assert failed['result']=='FAIL'
    assert failed['evidence']['component_checks'][0]['other_path']=='company_reference.customer_position'
    letter['normalized']['customer_position']=None
    assert run(10,[edd,letter])['result']=='FAIL'
    letter['normalized']['customer_position']='Account Executive'
    letter['normalized']['customer_name']='Another Person'
    assert run(10,[edd,letter])['result']=='FAIL'


def test_abbreviation_exception_does_not_apply_to_join_visit():
    assert run(4,[doc('ektp',name='Example Person'),doc('join_visit',customer_name='Example P.')])['result']=='FAIL'


def test_name_abbreviation_pass_needs_both_signature_observations(signed):
    publish_fixture(signed)
    config=signed.get('/api/config').json()
    config['payload']['maker_checker']=False
    assert signed.post('/api/config/publish',json={'expected_version':config['version'],'payload':config['payload']}).status_code==200
    case_id=upload(signed,names=('Synthetic_ektp.pdf','Synthetic_account opening.pdf'),template='account_opening').json()['case_ids'][0]
    process_all()
    with SessionLocal.begin() as db:
        docs=db.scalars(select(Document).where(Document.case_id==case_id)).all()
        for d in docs:
            d.normalized={**d.normalized,**({'name':'Example Person'} if d.doc_type=='ektp' else {'customer_name':'Example P.'})}
            d.validation={'fields':{}}
        refresh_case(db,case_id)
    process_all()
    case=signed.get('/api/cases/'+case_id).json()
    finding=next(f for f in case['reports'][0]['snapshot']['findings'] if f['rule_id']=='AO_SYSTEM_2')
    assert finding['result']=='REVIEW' and finding['evaluation_type']=='VISUAL'
    observations=[{'document_id':d['id'],'page':1,'region':'Synthetic customer signature execution area inspected'} for d in case['documents']]
    payload={'report_id':case['reports'][0]['id'],'rule_id':'AO_SYSTEM_2','result':'PASS','reason':'Synthetic regression: both customer signature regions were compared and match.','observations':observations[:1]}
    assert signed.post('/api/cases/'+case_id+'/sop-review',json=payload).status_code==422
    payload['observations']=observations
    assert signed.post('/api/cases/'+case_id+'/sop-review',json=payload).status_code==202
    process_all()
    after=signed.get('/api/cases/'+case_id).json()
    final=next(f for f in after['reports'][0]['snapshot']['findings'] if f['rule_id']=='AO_SYSTEM_2')
    assert final['result']=='PASS' and final['reason_code']=='VISUAL_REVIEW_PASS'
    assert len(final['evidence']['review']['observations'])==2


def test_official_seed_keeps_case_pins_forex_and_extraction_profiles(signed):
    publish_fixture(signed)
    case_id=upload(signed).json()['case_ids'][0]
    with SessionLocal.begin() as db:
        old=latest_config(db,'sqe'); payload=copy.deepcopy(old.payload)
        payload['seed_releases'].remove(RELEASE)
        nik=next(r for r in payload['sop_rules'] if r['id']=='AO_SYSTEM_1')
        policy=json.loads(nik['comparison_policy']);policy.pop('required_pattern');nik['comparison_policy']=json.dumps(policy)
        before_profiles=copy.deepcopy(payload['profiles'])
        before_forex=[r for r in payload['sop_rules'] if not r['id'].startswith('AO_')]
        pinned=db.get(Case,case_id).config_id
        db.add(Config(org='sqe',version=old.version+1,payload=payload,published_by='test.old-official'))
    seed_official_account_rules()
    with SessionLocal() as db:
        current=latest_config(db,'sqe');version=current.version
        assert len(current.published_by) <= 36
        assert current.payload['profiles']==before_profiles
        assert [r for r in current.payload['sop_rules'] if not r['id'].startswith('AO_')]==before_forex
        assert db.get(Case,case_id).config_id==pinned
        assert json.loads(next(r for r in current.payload['sop_rules'] if r['id']=='AO_SYSTEM_1')['comparison_policy'])['required_pattern']=='[0-9]{16}'
        validate_config(current.payload)
    seed_official_account_rules()
    with SessionLocal() as db:assert latest_config(db,'sqe').version==version
