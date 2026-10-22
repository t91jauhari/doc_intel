"""Resume one explicitly selected field request through the audited API."""
import argparse,copy,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.db import SessionLocal,Document,FieldReprocess,Job
from reviewer_field_cycle import client

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('document_id');p.add_argument('request_id');p.add_argument('baseline');p.add_argument('output');a=p.parse_args()
    before=json.loads(Path(a.baseline).read_text(encoding='utf-8'))
    assert before['document_id']==a.document_id
    with client() as c:
        response=c.post(f'/api/documents/{a.document_id}/reprocess-fields/{a.request_id}/retry',json={'accept_possible_duplicate_charge':False})
        response.raise_for_status();receipt=response.json()
    print(json.dumps({'action':'field_retry_accepted',**receipt}),flush=True)
    deadline=time.time()+900
    while time.time()<deadline:
        with SessionLocal() as db:
            job=db.get(Job,receipt['job_id']);status=job.status
        if status in ['COMPLETED','ERROR']:break
        time.sleep(2)
    with SessionLocal() as db:
        doc=db.get(Document,a.document_id);req=db.get(FieldReprocess,a.request_id);job=db.get(Job,receipt['job_id']);selected=set(req.payload['fields'])
        integrity={'untouched_raw_fields_preserved':{k:v for k,v in before['raw'].items() if k not in selected}=={k:v for k,v in doc.raw.items() if k not in selected},
                   'untouched_effective_fields_preserved':{k:v for k,v in before['normalized'].items() if k not in selected}=={k:v for k,v in doc.normalized.items() if k not in selected},
                   'reviewer_corrections_preserved':before['overrides']==doc.overrides}
        result={'document_id':doc.id,'request_id':req.id,'job_id':job.id,'job_status':job.status,'document_status':doc.status,'error':doc.error,
                'pending_submission':doc.provider_state.get('pending_create'),'fields':req.payload['fields'],
                'values':{k:doc.normalized.get(k) for k in selected},'integrity':integrity,'config_version':req.payload['config_version']}
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='values'}),flush=True)
    if job.status!='COMPLETED' or not all(integrity.values()):raise SystemExit(1)
