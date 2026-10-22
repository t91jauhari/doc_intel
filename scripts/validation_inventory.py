"""Inventory every invalid validation row and resolve it to a document-profile field.

No expected customer values are copied into extraction instructions.
"""
import argparse,json,re,sys
from pathlib import Path
from collections import Counter
import openpyxl
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.domain import default_config
from app.extraction_quality import apply_quality

def key(v):return re.sub(r'[^a-z0-9]','',str(v).casefold())
def inventory(path):
    config=apply_quality(default_config(),targets=[])
    docs={'invoice':'invoice','aplikasitransaksi':'application','formlld':'lld','formriplay':'riplay',
          'ektp':'ektp','suratpernyataanvalas1':'valas_declaration_1','suratpernyataanvalas2':'valas_declaration_2',
          'suratpenyataanvalas':'valas_declaration_1'}
    rows=[]
    book=openpyxl.load_workbook(path,data_only=True)
    for sheet in book:
        for number,row in enumerate(sheet.values,1):
            if len(row)<5 or not str(row[4]).casefold().startswith('invalid'):continue
            profile=docs.get(key(row[0]));field=None
            label=key(row[1])
            if profile:
                fields=config['profiles'][profile]['columns']
                field=next((k for k,v in fields if key(v)==label),None)
                if profile=='application' and label.startswith('acno'):
                    field='beneficiary_account_number' if 'penerima' in label else 'remitter_account_number'
            rows.append({'sheet':sheet.title,'row':number,'document':row[0],'label':row[1],
                         'profile':profile,'field':field,'status':row[4]})
    return rows

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('workbook');parser.add_argument('--output',required=True);args=parser.parse_args()
    rows=inventory(args.workbook)
    unresolved=[r for r in rows if not r['field']]
    Path(args.output).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    targets=sorted({(r['profile'],r['field']) for r in rows if r['field']})
    target_file=Path(__file__).resolve().parents[1]/'backend/app/config_data/validation_targets.json'
    target_file.write_text(json.dumps([{'profile':p,'field':f} for p,f in targets],indent=2),encoding='utf-8')
    print(json.dumps({'invalid_rows':len(rows),'targets':len(targets),'unresolved':unresolved,'statuses':dict(Counter(r['status'] for r in rows))},ensure_ascii=False))
    if unresolved:raise SystemExit(1)
