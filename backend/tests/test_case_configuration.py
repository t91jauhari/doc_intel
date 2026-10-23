"""Published-rule adoption is explicit, schema-compatible and receipt-preserving."""
import copy
from sqlalchemy import select,func
from app.db import SessionLocal,Case,Config,Document,Job,Report,Audit,CaseRun
from test_platform import upload,publish_fixture,process_all

def prepared(client):
 publish_fixture(client)
 cid=upload(client,names=('QA_ektp.pdf',),template='custom').json()['case_ids'][0]
 process_all()
 with SessionLocal() as db:
  case=db.get(Case,cid);old=db.get(Config,case.config_id)
  payload=copy.deepcopy(old.payload);version=old.version
 payload['report_title']='Updated QA report rules'
 response=client.post('/api/config/publish',json={'expected_version':version,'payload':payload})
 assert response.status_code==200,response.text
 return cid,version,response.json()['version']

def test_adoption_preserves_extraction_and_historical_report(signed):
 cid,old,new=prepared(signed)
 with SessionLocal() as db:
  before=[(d.id,d.raw,d.normalized,d.provider_state) for d in db.scalars(select(Document).where(Document.case_id==cid))]
  old_reports=[(r.id,copy.deepcopy(r.snapshot)) for r in db.scalars(select(Report).where(Report.case_id==cid))]
  jobs=db.scalar(select(func.count()).select_from(Job))
 r=signed.post(f'/api/cases/{cid}/configuration',json={'expected_version':old,'target_version':new,'reason':'Apply the approved page requirements.'})
 assert r.status_code==202,r.text
 with SessionLocal() as db:
  assert db.get(Config,db.get(Case,cid).config_id).version==new
  assert [(d.id,d.raw,d.normalized,d.provider_state) for d in db.scalars(select(Document).where(Document.case_id==cid))]==before
  assert db.scalar(select(func.count()).select_from(Job))==jobs
  for rid,snapshot in old_reports:assert db.get(Report,rid).snapshot==snapshot
  assert db.scalar(select(Audit).where(Audit.event=='case.configuration_adopted')).details['previous_version']==old
  assert db.scalar(select(CaseRun).where(CaseRun.case_id==cid,CaseRun.status=='QUEUED'))
 process_all()
 detail=signed.get('/api/cases/'+cid).json()
 assert detail['config_version']==new
 assert detail['reports'][0]['snapshot']['config_version']==new
 assert signed.post(f'/api/cases/{cid}/configuration',json={'expected_version':old,'target_version':new,'reason':'A stale update must not silently replace rules.'}).status_code==409

def test_adoption_rejects_busy_case(signed):
 cid,old,new=prepared(signed)
 with SessionLocal.begin() as db:
  d=db.scalar(select(Document).where(Document.case_id==cid));db.add(Job(org=d.org,document_id=d.id,branch_id=d.branch_id,action='revalidate',status='QUEUED'))
 r=signed.post(f'/api/cases/{cid}/configuration',json={'expected_version':old,'target_version':new,'reason':'Cannot change rules while processing runs.'})
 assert r.status_code==409,r.text

def test_adoption_rejects_incompatible_schema(signed):
 cid,old,new=prepared(signed)
 with SessionLocal.begin() as db:
  cfg=db.scalar(select(Config).where(Config.version==new));payload=copy.deepcopy(cfg.payload)
  from app.configuration.profiles import profile_schema
  schema=copy.deepcopy(profile_schema(payload,'ektp'));schema['properties']['unexpected_extra']={'type':'string'}
  payload['profiles']['ektp']['schema']=schema;cfg.payload=payload
 r=signed.post(f'/api/cases/{cid}/configuration',json={'expected_version':old,'target_version':new,'reason':'Schema changes need a separate data migration.'})
 assert r.status_code==409,r.text

def test_adoption_rejects_unpublished_version(signed):
 cid,old,new=prepared(signed)
 r=signed.post(f'/api/cases/{cid}/configuration',json={'expected_version':old,'target_version':new+100,'reason':'Only a published organization version is valid.'})
 assert r.status_code==404,r.text
