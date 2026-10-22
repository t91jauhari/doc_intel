"""Pristine normal-extraction repeats: new IDs, empty raw/overrides, no expected answers in prompts."""
import argparse,copy,json,sys,time,uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from sqlalchemy import select
from app.db import SessionLocal,Case,Document,Job,Batch,uid
from app.domain import latest_config,audit
from app.storage import original_key
from app.processor import process_job
from run_field_regression import score,text

SOURCES={'poko_lld':'899de05f-caf4-47d9-941e-39629950c338','bayu_lld':'ecd1ecd8-de60-4831-8f62-3e56f0ecb532','bayu_valas':'461c5879-fc08-4443-8ef4-8927cbb09c8f'}

def clone(db,source,case,batch_id):
    doc=Document(id=uid(),org=source.org,branch_id=source.branch_id,case_id=case.id,batch_id=batch_id,
      filename=source.filename,sha256=source.sha256,doc_type=source.doc_type,status='PROCESSING',validation_status='PENDING',
      classification={'manual':True,'type':source.doc_type,'confirmed':True,'method':'pristine_extraction_regression'},
      provider_state={'storage_key':original_key(source)},raw={},normalized={},overrides={},metadata_json={},validation={})
    job=Job(id=uid(),org=source.org,branch_id=source.branch_id,document_id=doc.id,action='process',status='RUNNING',lease_until=time.time()+1800)
    db.add_all([doc,job]);return doc,job

def run(repeat,root,rows,only_poko=False):
    with SessionLocal.begin() as db:
        originals={k:db.get(Document,i) for k,i in SOURCES.items()};cfg=latest_config(db,'sqe');plan={}
        for customer,keys in [('Poko',['poko_lld']),('Bayu',['bayu_lld','bayu_valas'])]:
            if only_poko and customer!='Poko':continue
            old=db.get(Case,originals[keys[0]].case_id)
            case=Case(id=uid(),org=old.org,branch_id=old.branch_id,reference=f'PROMPT-REPLAY-{repeat}-{uuid.uuid4().hex[:6]}',customer=f'Prompt replay {repeat} — {customer}',template=old.template,created_by=old.created_by,config_id=cfg.id,status='PROCESSING',validation_status='PENDING')
            db.add(case);db.flush()
            batch=Batch(id=uid(),org=old.org,branch_id=old.branch_id,created_by=old.created_by,idempotency_key=f'prompt-replay-{uuid.uuid4()}');db.add(batch)
            for key in keys:plan[key]=clone(db,originals[key],case,batch.id)
            audit(db,old.org,'worker','regression.pristine_case_created',old.branch_id,case.id,config_version=cfg.version,source_case_id=old.id,repeat=repeat)
    # The context source is genuinely extracted first; no copied normalized source values.
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda key:process_job(plan[key][1].id),[key for key in ['poko_lld','bayu_lld'] if key in plan]))
    if 'bayu_valas' in plan:process_job(plan['bayu_valas'][1].id)
    results=[]
    with SessionLocal() as db:
        for key in ['poko_lld','bayu_valas']:
            if key not in plan:continue
            doc=db.get(Document,plan[key][0].id);job=db.get(Job,plan[key][1].id)
            customer='Poko' if key=='poko_lld' else 'Bayu'
            fields=['beneficiary_address','bank_officer_signature'] if key=='poko_lld' else ['customer_address']
            for field in fields:
                ref=next(r for r in rows if r['Customer']==customer and r['Profile Field Key']==field and r['Document ID']==SOURCES[key])
                actual=doc.normalized.get(field)
                results.append({'repeat':repeat,'customer':customer,'field':field,'document_id':doc.id,'source_document_id':SOURCES[key],
                    'config_version':cfg.version,'job_status':job.status,'error':job.error,'expected':ref['Source Value'],'actual':text(actual),
                    'raw_model_value':doc.raw.get(field),'override_count':len(doc.overrides),'automatic_context':doc.validation.get('automatic_context'),
                    'comparison':score(ref['Source Value'],actual,field) if job.status=='COMPLETED' else 'Unable to verify'})
    (root/f'fresh-repeat-{repeat}.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'repeat':repeat,'results':results},ensure_ascii=False),flush=True)
    return results

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('reviewed_results');p.add_argument('--output',required=True);p.add_argument('--repeats',type=int,default=2);p.add_argument('--only-poko',action='store_true');a=p.parse_args()
    rows=json.loads(Path(a.reviewed_results).read_text(encoding='utf-8'));root=Path(a.output);root.mkdir(parents=True,exist_ok=True)
    all_rows=[]
    for repeat in range(1,a.repeats+1):
        all_rows.extend(run(repeat,root,rows,a.only_poko));(root/'fresh-results.json').write_text(json.dumps(all_rows,ensure_ascii=False,indent=2),encoding='utf-8')
