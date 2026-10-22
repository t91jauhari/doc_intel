"""Apply a reviewer-note plan through existing audited APIs; never pass expected answers to extraction."""
import argparse,copy,json,os,sys,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import httpx
from app.db import SessionLocal,Document,Job
from run_field_regression import score,text

REFERENCE_FIELDS={('Artha','document_date'),('Sri P','swift_code'),('Indah','remitter_account_number'),('Indah','currency'),
 ('Poko','charges'),('Poko','from_address'),('Poko','payer_identification_number'),('Bayu','depository_correspondent_bank_country_code'),
 ('Bayu','signatory'),('Steve','notes'),('Steve','depository_correspondent_bank_country_code'),('Dirman','birth_date'),('Steve','bank_address')}
DISPLAY_FIELDS={('Bayu','charges'),('Dirman','transaction_type')}

def plan(rows):
    for row in rows:
        pair=(row['Customer'],row['Profile Field Key'])
        row['action']='reference_correction' if pair in REFERENCE_FIELDS else 'display_fix' if pair in DISPLAY_FIELDS else 'reprocess'
        row['approved_reference']=row['System Value'] if row['action']=='reference_correction' else row['Source Value']
        if pair==('Indah','remitter_account_number'):row['approved_reference']='0800997624'
        if pair==('Dirman','birth_date'):row['approved_reference']='06-05-1994'
        row['reference_reason']='Reviewer explicitly accepted the extracted value.' if pair in REFERENCE_FIELDS else ''
        if pair==('Steve','bank_address'):row['reference_reason']='Original invoice bank block visibly spells Foshan. Reference Fushan conflicts with original; retain exact printed spelling.'
        if pair==('Poko','beneficiary'):
            row['approved_reference']='ORANGE SOFTWARE (HK) Ltd., 9300 Flair Drive, 4th, El monte, CA, 91731 Pasadena, USA'
            row['reference_corrected']=True
            row['reference_reason']='Original application enlarged recipient panel reads 4th (not P4th) and includes the continuation 91731 Pasadena, USA. Reviewer requested the complete combined name/address/phone value; reference corrected to the full visible block.'
    return rows

@contextmanager
def client():
    c=httpx.Client(base_url='http://127.0.0.1:8000',timeout=60)
    try:
        r=c.post('/api/auth/login',json={'organization':os.getenv('DEV_ORGANIZATION','sqe'),'email':os.getenv('DEV_EMAIL','sqe@bic.local'),'password':os.getenv('DEV_PASSWORD','P@ssw0rd2026')});r.raise_for_status();c.headers['X-CSRF-Token']=r.json()['csrf'];yield c
    finally:c.close()

def run(rows,output,only_unresolved=False):
    groups={}
    with SessionLocal() as db:
        for row in rows:
            if row['action']=='reprocess':
                doc=db.get(Document,row['Document ID'])
                if only_unresolved and score(row['approved_reference'],doc.normalized.get(row['Profile Field Key']),row['Profile Field Key'])=='Valid (same result)':continue
                groups.setdefault(row['Document ID'],[]).append(row)
    results=[]
    def one(item):
        docid,items=item;fields=sorted({r['Profile Field Key'] for r in items})
        with client() as c:
            response=c.post(f'/api/documents/{docid}/reprocess-fields',json={'fields':fields,'reason':'Reviewer workbook remediation, October 2026','use_latest_config':True})
            if response.status_code!=202:return {'document_id':docid,'status':'ERROR','error':response.text,'fields':fields}
            receipt=response.json();deadline=time.time()+1200
            while time.time()<deadline:
                with SessionLocal() as db:j=db.get(Job,receipt['job_id']);status=j.status;error=j.error
                if status in ['COMPLETED','ERROR']:break
                time.sleep(3)
            with SessionLocal() as db:d=db.get(Document,docid);values=copy.deepcopy(d.normalized)
            result={'document_id':docid,'fields':fields,'status':status,'error':error,**receipt,
                    'rows':[{'excel_row':r['excel_row'],'value':values.get(r['Profile Field Key']),'comparison':score(r['approved_reference'],values.get(r['Profile Field Key']),r['Profile Field Key']) if status=='COMPLETED' else 'Unable to verify'} for r in items]}
            print(json.dumps({'document_id':docid,'customer':items[0]['Customer'],'status':status,'fields':len(fields),'comparisons':[r['comparison'] for r in result['rows']],'error':error}),flush=True)
            return result
    with ThreadPoolExecutor(max_workers=2) as pool:
        for result in pool.map(one,groups.items()):
            results.append(result);Path(output).write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('notes');p.add_argument('--output',required=True);p.add_argument('--plan-only',action='store_true');p.add_argument('--only-unresolved',action='store_true');args=p.parse_args()
    rows=plan(json.loads(Path(args.notes).read_text(encoding='utf-8')))
    Path(args.output+'.plan.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    if not args.plan_only:run(rows,args.output,args.only_unresolved)
