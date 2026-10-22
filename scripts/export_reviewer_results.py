"""Snapshot current effective results, compare to reviewed references, and prove untouched values."""
import argparse,copy,csv,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from sqlalchemy import select
from app.db import SessionLocal,Document,FieldReprocess,Job
from reviewer_field_cycle import plan
from run_field_regression import score,text

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('notes');p.add_argument('baseline');p.add_argument('--output',required=True);a=p.parse_args()
    rows=plan(json.loads(Path(a.notes).read_text(encoding='utf-8')))
    baseline=json.loads(Path(a.baseline).read_text(encoding='utf-8'))
    output=Path(a.output);output.mkdir(parents=True,exist_ok=True)
    with SessionLocal() as db:
        requests=list(db.scalars(select(FieldReprocess).order_by(FieldReprocess.created_at.desc())))
        requests=[r for r in requests if r.payload.get('reason')=='Reviewer workbook remediation, October 2026']
        integrity=[]
        for docid,before in baseline.items():
            doc=db.get(Document,docid);selected={r['Profile Field Key'] for r in rows if r['Document ID']==docid}
            integrity.append({'Document ID':docid,'Filename':doc.filename,
              'Untouched Raw Fields Preserved':{k:v for k,v in before['raw'].items() if k not in selected}=={k:v for k,v in doc.raw.items() if k not in selected},
              'Untouched Effective Fields Preserved':{k:v for k,v in before['normalized'].items() if k not in selected}=={k:v for k,v in doc.normalized.items() if k not in selected}})
        for row in rows:
            doc=db.get(Document,row['Document ID']);key=row['Profile Field Key']
            req=next((r for r in requests if r.document_id==doc.id and key in r.payload['fields']),None)
            value=copy.deepcopy(doc.normalized.get(key))
            original_source=row['Source Value'];original_system=row['System Value']
            row.update({'Original Source Value':original_source,'Original System Value':original_system,
                        'Source Value':row['approved_reference'],'System Value':text(value),
                        'Comparison Result':score(row['approved_reference'],value,key),'Current Structured Value':value})
            if key in doc.overrides:
                method='Audited reviewer correction'
                applied='Reviewer-authorized same-case address reconciliation; original raw extraction retained.' if row['Customer']=='Bayu' and key=='customer_address' else 'User explicitly confirmed letter L in the leading address unit Al. Effective address corrected through the audited API; original raw image reading retained.'
            elif row['action']=='reference_correction':
                method='Reference corrected'
                applied=row['reference_reason']
            elif row['action']=='display_fix':
                method='Display and comparison fixed'
                applied='Previously stored fee amount or Other description is now included in the combined display. No extra model call required.'
            else:
                method='Re-extracted from original'
                applied='Published field guidance refined and selected fields reread from original pages; enlarged original regions used where configured.'
                if row.get('reference_corrected'):
                    method+='; reference corrected';applied+=' '+row['reference_reason']
            row['Resolution Method']=method;row['Fix Applied']=applied
            row['Evidence Status']='Validated against reviewed reference' if row['Comparison Result']=='Valid (same result)' else 'Needs clarification or further correction'
            if req:
                row['Request ID']=req.id;row['Latest Job Status']=db.get(Job,req.job_id).status
            else:row['Latest Job Status']='No new provider request needed'
        jobs=[{'request_id':r.id,'document_id':r.document_id,'fields':r.payload['fields'],'status':db.get(Job,r.job_id).status,'error':db.get(Job,r.job_id).error,'config_version':r.payload['config_version']} for r in requests]
    (output/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'jobs.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'integrity.json').write_text(json.dumps(integrity,indent=2),encoding='utf-8')
    fields=['Document Name','Customer','Field Name','Source Value','System Value','Comparison Result','How to Solve It','Resolution Method','Fix Applied','Original Source Value','Original System Value','Profile Field Key','Document ID','Request ID','Latest Job Status']
    with (output/'Reviewed_Field_Fixes_Results.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields,quoting=csv.QUOTE_ALL,extrasaction='ignore');w.writeheader();w.writerows(rows)
    summary={'reviewed_fields':len(rows),'valid':sum(r['Comparison Result']=='Valid (same result)' for r in rows),
             'invalid':sum(r['Comparison Result']!='Valid (same result)' for r in rows),'provider_requests':len(jobs),
             'provider_errors':sum(j['status']!='COMPLETED' for j in jobs),'documents_checked':len(integrity),
             'untouched_fields_preserved':all(r['Untouched Raw Fields Preserved'] and r['Untouched Effective Fields Preserved'] for r in integrity)}
    (output/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary))
