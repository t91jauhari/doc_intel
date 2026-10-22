"""Second extraction pass for a visually confirmed model-column omission."""
import json,os,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import httpx
from sqlalchemy import select
from app.db import SessionLocal,Document,FieldReprocess,Job
from app.extraction_quality import seed_quality
seed_quality()
with SessionLocal() as db:
    candidates=list(db.scalars(select(FieldReprocess).order_by(FieldReprocess.created_at.desc())))
    doc=next(db.get(Document,r.document_id) for r in candidates if db.get(Document,r.document_id).filename=='Forex - Steve Captain - Invoice.pdf')
with httpx.Client(base_url='http://127.0.0.1:8000',timeout=60) as client:
    login=client.post('/api/auth/login',json={'organization':os.getenv('DEV_ORGANIZATION','sqe'),'email':os.getenv('DEV_EMAIL','sqe@bic.local'),'password':os.getenv('DEV_PASSWORD','P@ssw0rd2026')});login.raise_for_status();client.headers['X-CSRF-Token']=login.json()['csrf']
    response=client.post(f'/api/documents/{doc.id}/reprocess-fields',json={'fields':['item_name','ship_to_address'],'reason':'Validation workbook invoice refinement pass 2','use_latest_config':True})
    response.raise_for_status();receipt=response.json()
    deadline=time.time()+900
    while time.time()<deadline:
        with SessionLocal() as db:job=db.get(Job,receipt['job_id']);status=job.status
        if status in ['COMPLETED','ERROR']:break
        time.sleep(3)
    print(json.dumps({'request_id':receipt['request_id'],'document_id':doc.id,'status':status,'error':job.error}),flush=True)
