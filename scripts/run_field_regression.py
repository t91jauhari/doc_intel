"""Re-extract invalid workbook fields against stored originals, in bounded batches.

Expected answers are read only for scoring, never included in reprocess requests.
Run inside the API container after deploying the release.
"""
import argparse,copy,csv,datetime,json,re,sys,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import httpx,openpyxl
from sqlalchemy import select
from app.db import SessionLocal,Case,Document,Job
from app.value_display import display_value
from app.settings import settings
from validation_inventory import inventory

def norm(v):return re.sub(r'[^\w]','',str(v).casefold())
def text(v):
    if isinstance(v,datetime.datetime):return v.strftime('%d-%m-%Y')
    if isinstance(v,float) and v.is_integer():return str(int(v))
    return display_value(v)
def score(expected,actual,field):
    a,b=text(expected),text(actual)
    if field=='beneficiary_bank' and isinstance(actual,dict) and {'name','branch'}<=set(actual):
        # The bank and geographic branch may be displayed in either order.
        if sorted(re.findall(r'\w+',a.casefold()))==sorted(re.findall(r'\w+',b.casefold())):
            return 'Valid (same result)'
    if field=='transaction_type' and 'lainnya' in a.casefold() and 'lainnya' in b.casefold():
        if norm(re.sub(r'\bother\b','',a,flags=re.I))==norm(re.sub(r'\bother\b','',b,flags=re.I)):
            return 'Valid (same result)'
    if field=='charges' and isinstance(actual,dict) and actual.get('raw'):
        # Compare the selected method AND fee; do not hide a missing amount.
        from app.dataset_comparison import number
        def method(v):
            v=re.sub(r'\bdebit\s*a/?c\b','',v,flags=re.I)
            v=re.sub(r'\bdebet\b','debit',v,flags=re.I)
            return norm(re.sub(r'(?:USD|EUR|CNY|IDR|\$)?\s*\d[\d., ]*','',v,flags=re.I))
        amount=re.search(r'(?:USD|EUR|CNY|IDR|\$)?\s*\d[\d., ]*',a,flags=re.I)
        if amount and method(a)==method(text(actual.get('selected'))):
            try:
                ca,na=number(amount[0].replace('$','').strip());cb,nb=number(str(actual['raw']).replace('$','').strip())
                if na==nb and (not ca or not cb or ca==cb) and (('$' in a)==('$' in b)):
                    return 'Valid (same result)'
            except ValueError:pass
    numeric_field=any(part in field for part in ['amount','subtotal','discount','shipping','price','charges','exchange_rate'])
    if numeric_field and bool(re.search(r'(^|[^\w])-\s*\d',a)) != bool(re.search(r'(^|[^\w])-\s*\d',b)):
        return 'Invalid (different value)'
    if field in ['item_name','quantity','unit_price']:
        a=re.sub(r'(?m)^\s*\d+\.\s*','',a)
    # Numeric punctuation carries value: 1.00 must never equal 100.
    # Keep literal equality for unit-bearing amounts that the numeric parser
    # deliberately leaves for review, but do not strip their separators.
    literal_equal=a.strip().casefold()==b.strip().casefold()
    if literal_equal or (not numeric_field and norm(a)==norm(b)):return 'Valid (same result)'
    if field=='page_initials':
        marks=re.findall(r'Page \d+: (Present|Absent)',b)
        if marks and all(m=='Absent' for m in marks) and (a.casefold().startswith('not available') or a.casefold().startswith('[blank')):return 'Valid (same result)'
        if marks and all(m=='Present' for m in marks) and a.casefold().startswith('available'):return 'Valid (same result)'
    if numeric_field:
        from app.dataset_comparison import number
        try:
            ca,na=number(a);cb,nb=number(b)
            if na==nb and (not ca or not cb or ca==cb):return 'Valid (same result)'
        except ValueError:pass
        if field in ['subtotal_all_items','subtotal_less_discount','final_total_amount']:
            # Invoice totals use monetary grouping, not three-place unit-price precision.
            def grouped(v):
                m=re.fullmatch(r'\s*(?:(USD|EUR|CNY|IDR|SGD|GBP|AUD|HKD)\s*)?(-?\d{1,3}(?:[.,]\d{3})+|-?\d+)\s*',v,re.I)
                return (m[1].upper() if m[1] else None,int(re.sub('[.,]','',m[2]))) if m else None
            ga,gb=grouped(a),grouped(b)
            if ga and gb and ga[1]==gb[1] and (ga[0] or gb[0]) and (not ga[0] or not gb[0] or ga[0]==gb[0]):return 'Valid (same result)'
    if a.strip().casefold() in ['[blank]','[blank])','[blank}',']blank]','n/a'] and (actual is None or b in ['Missing','None selected'] or b.startswith('Absent')):return 'Valid (same result)'
    if a.casefold().startswith('available') and (b.startswith('Present') or actual is True):return 'Valid (same result)'
    if a.casefold().startswith('not available') and (b.startswith('Absent') or actual is False):return 'Valid (same result)'
    if 'date' in field:
        from app.dataset_comparison import canonical
        try:
            if canonical(a,'date')==canonical(b,'date'):return 'Valid (same result)'
        except ValueError:pass
    return 'Invalid (different value)'

def run(workbook,output,limit=None,skip_completed=None):
    book=openpyxl.load_workbook(workbook,data_only=True)
    rows=inventory(workbook)
    with SessionLocal() as db:
        cases=list(db.scalars(select(Case).order_by(Case.created_at.desc())))
        docs=list(db.scalars(select(Document).where(Document.status=='COMPLETED').order_by(Document.created_at.desc())))
    groups={};skipped=[]
    for item in rows:
        candidates=[c for c in cases if norm(c.customer).startswith(norm(item['sheet'])) or norm(item['sheet']).startswith(norm(c.customer))]
        selected=next((d for c in candidates for d in docs if d.case_id==c.id and d.doc_type==item['profile'] and d.raw),None)
        if not selected:
            skipped.append({**item,'reason':'No completed matching stored document'});continue
        entry=groups.setdefault(selected.id,{'doc':selected,'rows':[]})
        entry['rows'].append(item)
    selected=list(groups.values())[:limit] if limit else list(groups.values())
    if skip_completed:
        prior=json.loads(Path(skip_completed).read_text(encoding='utf-8'))
        finished={r['document_id'] for r in prior if r.get('status')=='COMPLETED'}
        selected=[g for g in selected if g['doc'].id not in finished]
    root=Path(output);root.mkdir(parents=True,exist_ok=True)
    (root/'plan.json').write_text(json.dumps({'groups':[{'document_id':g['doc'].id,'filename':g['doc'].filename,'fields':sorted({r['field'] for r in g['rows']})} for g in selected],'skipped':skipped},indent=2),encoding='utf-8')
    results=[]
    def process(group):
        d=group['doc'];before=copy.deepcopy(d.raw);fields=sorted({r['field'] for r in group['rows']})
        import os
        with httpx.Client(base_url='http://127.0.0.1:8000',timeout=60) as client:
            login=client.post('/api/auth/login',json={'organization':os.getenv('DEV_ORGANIZATION','sqe'),'email':os.getenv('DEV_EMAIL','sqe@bic.local'),'password':os.getenv('DEV_PASSWORD','P@ssw0rd2026')})
            login.raise_for_status();client.headers['X-CSRF-Token']=login.json()['csrf']
            response=client.post(f'/api/documents/{d.id}/reprocess-fields',json={'fields':fields,'reason':'Validation workbook invalid-field regression','use_latest_config':True})
            if response.status_code!=202:return {'document_id':d.id,'error':response.text,'rows':[]}
            receipt=response.json();deadline=time.time()+900
            while time.time()<deadline:
                with SessionLocal() as db:status=db.get(Job,receipt['job_id']).status
                if status in ['COMPLETED','ERROR']:break
                time.sleep(3)
            with SessionLocal() as db:
                updated=db.get(Document,d.id);job=db.get(Job,receipt['job_id'])
                unchanged={k:v for k,v in updated.raw.items() if k not in fields}=={k:v for k,v in before.items() if k not in fields}
                values=copy.deepcopy(updated.normalized)
            compared=[]
            for item in group['rows']:
                source=book[item['sheet']].cell(item['row'],3).value
                actual=values.get(item['field'])
                compared.append({'Customer':item['sheet'],'Document Name':item['document'],'Field Name':item['label'],
                    'Source Value':text(source),'Previous System Value':text(book[item['sheet']].cell(item['row'],4).value),
                    'System Value':text(actual),'Comparison Result':score(source,actual,item['field']) if job.status=='COMPLETED' else 'Unable to verify',
                    'Notes':f'Field job {job.status}; untouched fields preserved: {unchanged}',
                    'Document ID':d.id,'Request ID':receipt['request_id']})
            print(json.dumps({'document':d.filename,'status':job.status,'fields':len(fields),'untouched_preserved':unchanged,'error':job.error}),flush=True)
            return {'document_id':d.id,'status':job.status,'request_id':receipt['request_id'],'unchanged':unchanged,'error':job.error,'rows':compared}
    with ThreadPoolExecutor(max_workers=2) as pool:
        for result in pool.map(process,selected):
            results.append(result)
            (root/'run.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    flat=[r for result in results for r in result['rows']]
    if flat:
        with (root/'field-regression.csv').open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(flat[0]),quoting=csv.QUOTE_ALL);writer.writeheader();writer.writerows(flat)
    summary={'documents':len(results),'completed':sum(r.get('status')=='COMPLETED' for r in results),
             'errors':sum(r.get('status')!='COMPLETED' for r in results),'fields_scored':len(flat),
             'valid_after':sum(r['Comparison Result']=='Valid (same result)' for r in flat),
             'unchanged_fields_preserved':all(r.get('unchanged',False) for r in results),'skipped':skipped,
             'note':'Only previously invalid workbook rows scored; this is not a whole-dataset accuracy percentage. Reference answers never supplied to provider.'}
    (root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(summary),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('workbook');p.add_argument('--output',required=True);p.add_argument('--limit',type=int);p.add_argument('--skip-completed');a=p.parse_args();run(a.workbook,a.output,a.limit,a.skip_completed)
