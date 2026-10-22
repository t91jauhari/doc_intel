"""Read-only export of normal-extraction regression cases, never used as model input."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from sqlalchemy import select
from app.db import SessionLocal,Case,Config,Document,Job
from fresh_profile_replay import SOURCES
from run_field_regression import score,text

def export(references):
    rows=[]
    with SessionLocal() as db:
        for case in db.scalars(select(Case).where(Case.reference.like('PROMPT-REPLAY-%'))):
            cfg=db.get(Config,case.config_id)
            for doc in db.scalars(select(Document).where(Document.case_id==case.id)):
                customer='Poko' if case.customer.endswith('Poko') else 'Bayu'
                key='poko_lld' if customer=='Poko' and doc.doc_type=='lld' else 'bayu_valas' if customer=='Bayu' and doc.doc_type=='valas_declaration_1' else None
                if key is None:continue
                job=db.scalars(select(Job).where(Job.document_id==doc.id,Job.action=='process')).first()
                for field in (['beneficiary_address','bank_officer_signature'] if key=='poko_lld' else ['customer_address']):
                    ref=next(r for r in references if r['Customer']==customer and r['Profile Field Key']==field and r['Document ID']==SOURCES[key])
                    actual=doc.normalized.get(field)
                    rows.append({'case_reference':case.reference,'customer':customer,'field':field,'document_id':doc.id,
                        'source_document_id':SOURCES[key],'config_version':cfg.version,'release':cfg.payload.get('extraction_quality_release'),
                        'job_status':job.status if job else None,'expected':ref['Source Value'],'actual':text(actual),
                        'raw_model_value':doc.raw.get(field),'override_count':len(doc.overrides),
                        'automatic_context':doc.validation.get('automatic_context'),
                        'comparison':score(ref['Source Value'],actual,field) if job and job.status=='COMPLETED' else 'Unable to verify'})
    return sorted(rows,key=lambda r:(r['config_version'],r['case_reference'],r['field']))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('references');p.add_argument('output');a=p.parse_args()
    rows=export(json.loads(Path(a.references).read_text(encoding='utf-8')))
    Path(a.output).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'observations':len(rows),'valid':sum(r['comparison'].startswith('Valid') for r in rows),'config_versions':sorted({r['config_version'] for r in rows})}))
