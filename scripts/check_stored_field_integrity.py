"""Read-only comparison of untouched fields against a pre-run document baseline."""
import argparse,csv,json,sys
from pathlib import Path
from collections import defaultdict
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from sqlalchemy import select
from app.db import SessionLocal,FieldReprocess,Document,Job

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('baseline');p.add_argument('--output',required=True);a=p.parse_args()
    baseline=json.loads(Path(a.baseline).read_text(encoding='utf-8'));groups=defaultdict(list)
    with SessionLocal() as db:
        for req in db.scalars(select(FieldReprocess)):
            if req.payload.get('reason','').startswith('Validation workbook'):groups[req.document_id].append(req)
        rows=[]
        for doc_id,requests in groups.items():
            doc=db.get(Document,doc_id);before=baseline[doc_id];selected={key for req in requests for key in req.payload['fields']}
            raw_ok={k:v for k,v in doc.raw.items() if k not in selected}=={k:v for k,v in before['raw'].items() if k not in selected}
            normalized_ok={k:v for k,v in doc.normalized.items() if k not in selected}=={k:v for k,v in before['normalized'].items() if k not in selected}
            failed=all(db.get(Job,r.job_id).status=='ERROR' for r in requests)
            failure_preserved=(doc.raw==before['raw'] and doc.normalized==before['normalized']) if failed else 'N/A'
            rows.append({'Document Name':doc.filename,'Document ID':doc_id,'Selected Field Count':len(selected),
                'Untouched Raw Fields Preserved':raw_ok,'Untouched Effective Fields Preserved':normalized_ok,
                'Original Values Retained On Failure':failure_preserved})
    with Path(a.output).open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),quoting=csv.QUOTE_ALL);writer.writeheader();writer.writerows(rows)
    print(json.dumps({'documents':len(rows),'all_untouched_raw_preserved':all(r['Untouched Raw Fields Preserved'] for r in rows),
        'all_untouched_effective_preserved':all(r['Untouched Effective Fields Preserved'] for r in rows),
        'all_failed_requests_preserved_originals':all(r['Original Values Retained On Failure'] in [True,'N/A'] for r in rows)}))
    if any(not r['Untouched Raw Fields Preserved'] or not r['Untouched Effective Fields Preserved'] or r['Original Values Retained On Failure'] is False for r in rows):raise SystemExit(1)
