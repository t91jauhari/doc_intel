"""Explicitly retry validation field requests rejected with HTTP 503, once.

Requires the operator's acknowledgement flag; cached completed pages are reused.
"""
import argparse,copy,json,os,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import httpx
from sqlalchemy import select
from app.db import SessionLocal,FieldReprocess,Document,Job

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--accept-possible-duplicate-charge',action='store_true');p.add_argument('--output',required=True);a=p.parse_args()
    if not a.accept_possible_duplicate_charge:raise SystemExit('Explicit possible-duplicate-charge acknowledgement required.')
    with SessionLocal() as db:
        ids=[r.id for r in db.scalars(select(FieldReprocess)) if r.payload.get('reason')=='Validation workbook invalid-field regression' and db.get(Job,r.job_id).status=='ERROR' and 'HTTP 503' in db.get(Job,r.job_id).error]
    results=[]
    with httpx.Client(base_url='http://127.0.0.1:8000',timeout=60) as client:
        login=client.post('/api/auth/login',json={'organization':os.getenv('DEV_ORGANIZATION','sqe'),'email':os.getenv('DEV_EMAIL','sqe@bic.local'),'password':os.getenv('DEV_PASSWORD','P@ssw0rd2026')});login.raise_for_status();client.headers['X-CSRF-Token']=login.json()['csrf']
        for request_id in ids:
            with SessionLocal() as db:
                req=db.get(FieldReprocess,request_id);doc=db.get(Document,req.document_id);before=copy.deepcopy(doc.raw)
            response=client.post(f'/api/documents/{doc.id}/reprocess-fields/{request_id}/retry',json={'accept_possible_duplicate_charge':True})
            response.raise_for_status();job_id=response.json()['job_id'];deadline=time.time()+900
            while time.time()<deadline:
                with SessionLocal() as db:status=db.get(Job,job_id).status
                if status in ['ERROR','COMPLETED']:break
                time.sleep(3)
            with SessionLocal() as db:
                updated=db.get(Document,doc.id);job=db.get(Job,job_id)
                untouched=all(updated.raw.get(k)==v for k,v in before.items() if k not in req.payload['fields'])
                result={'request_id':request_id,'document_id':doc.id,'filename':doc.filename,'status':job.status,'error':job.error,'untouched_preserved':untouched}
            results.append(result);Path(a.output).write_text(json.dumps(results,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
