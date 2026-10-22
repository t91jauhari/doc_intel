import copy,time
from types import SimpleNamespace
from sqlalchemy import select,func
from app.db import Case,Report,SessionLocal
from app.main import report_download_name

def seed_report(signed):
    cfg=signed.get('/api/config').json()
    user=signed.get('/api/auth/session').json()['user']
    branch=signed.get('/api/branches').json()[0]['id']
    with SessionLocal.begin() as db:
        case=Case(org='sqe',branch_id=branch,customer='Sri P',reference='Sri P / test',template='forex',created_by=user['id'],config_id=cfg['id'],status='NEEDS_REVIEW')
        db.add(case);db.flush()
        snapshot={'customer':'Sri P','reference':case.reference,'validation_status':'REVIEW','provider':'fixture','findings':[],'documents':[],'missing':[]}
        old=Report(org='sqe',branch_id=branch,case_id=case.id,version=1,fingerprint='first',snapshot=snapshot,created_at=time.time()-10)
        new=Report(org='sqe',branch_id=branch,case_id=case.id,version=2,fingerprint='second',snapshot=snapshot,created_at=time.time())
        db.add_all([old,new]);db.flush()
        return case.id,old.id,new.id,branch,cfg['id'],user['id']

def test_latest_customer_report_and_separate_flows(signed):
    case_id,old,new,branch,config_id,user_id=seed_report(signed)
    with SessionLocal.begin() as db:
        original=db.get(Report,new)
        # A duplicate upload for the same customer/service is not another list row.
        duplicate=Case(org='sqe',branch_id=branch,customer=' sri p ',reference='duplicate',template='forex',created_by=user_id,config_id=config_id,status='NEEDS_REVIEW')
        other=Case(org='sqe',branch_id=branch,customer='Sri P',reference='opening',template='account_opening',created_by=user_id,config_id=config_id,status='NEEDS_REVIEW')
        db.add_all([duplicate,other]);db.flush()
        extra=[]
        for c in [duplicate,other]:
            r=Report(org='sqe',branch_id=branch,case_id=c.id,version=1,fingerprint=c.id,snapshot=copy.deepcopy(original.snapshot),created_at=original.created_at+10)
            db.add(r);db.flush();extra.append(r.id)
    response=signed.get('/api/reports')
    assert response.status_code==200,response.text
    assert {r['id'] for r in response.json()}==set(extra)
    with SessionLocal() as db:assert db.scalar(select(func.count()).select_from(Report))==4

def test_report_detail_resolves_latest_and_download_has_customer(signed):
    case_id,old,new,*_=seed_report(signed)
    detail=signed.get(f'/api/reports/{old}')
    assert detail.status_code==200,detail.text
    assert detail.json()['id']==new and detail.json()['version']==2
    assert detail.json()['snapshot']['customer']=='Sri P'
    response=signed.get(f'/api/reports/{new}/download?format=json')
    assert response.status_code==200,response.text
    assert 'kertas-kerja-Sri P-v2.json' in response.headers['content-disposition']
    assert signed.get('/api/reports/not-a-report').status_code==404
    with SessionLocal.begin() as db:db.get(Report,new).org='other-organization'
    assert signed.get(f'/api/reports/{new}').status_code==404
    assert signed.get(f'/api/reports/{new}/download?format=json').status_code==404
    assert signed.get(f'/api/reports/{old}').json()['id']==old

def test_filenames_safely_preserve_customer_and_format():
    report=SimpleNamespace(snapshot={'customer':'Paulus / "王"\r\n'},version=7)
    for fmt in ['pdf','xlsx','json']:
        name=report_download_name(report,fmt)
        assert '\r' not in name and '\n' not in name
        assert 'Paulus' in name and f'-v7.{fmt}' in name
        assert "filename*=UTF-8''" in name and '%E7%8E%8B' in name
