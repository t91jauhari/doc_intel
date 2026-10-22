"""Persist specifically approved reference edits and the explicitly requested same-case address correction."""
import copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from sqlalchemy import select
from app.db import SessionLocal,Document,DatasetComparison
from reviewer_field_cycle import plan,client
from run_field_regression import score

def apply(rows):
    log=[]
    with client() as c:
        # Reviewer explicitly authorized this fallback after the reread still differed.
        row=next(r for r in rows if r['Customer']=='Bayu' and r['Profile Field Key']=='customer_address')
        with SessionLocal() as db:
            target=db.get(Document,row['Document ID']);before=copy.deepcopy(target.normalized['customer_address'])
            sources=[d for d in db.scalars(select(Document).where(Document.case_id==target.case_id)) if d.doc_type=='lld']
            source=next(d for d in sources if score(row['approved_reference'],d.normalized.get('payer_address'),'payer_address')=='Valid (same result)')
            value={'raw':source.normalized['payer_address']['raw'],'complete':True}
        if score(row['approved_reference'],before,'customer_address')!='Valid (same result)':
            reason=f'Reviewer workbook authorized same-case address reconciliation after unsuccessful reread. Verified payer_address copied from LLD document {source.id}; raw declaration observation retained.'
            response=c.post(f'/api/documents/{target.id}/effective-corrections',json={'field':'customer_address','expected_value':before,'value':value,'reason':reason})
            response.raise_for_status()
            log.append({'action':'reviewer_cross_document_correction','document_id':target.id,'field':'customer_address','source_document_id':source.id,'before':before,'after':value,'reason':reason})
        grouped={}
        with SessionLocal() as db:
            for row in rows:
                if row['action']=='reference_correction' or row.get('reference_corrected'):grouped.setdefault(db.get(Document,row['Document ID']).case_id,[]).append(row)
        samples={'Artha':'3','Sri P':'2','Indah':'1','Poko':'5','Bayu':'7','Steve':'10','Dirman':'6'}
        for caseid,items in grouped.items():
            dataset=c.get(f'/api/dataset-sample?case_id={caseid}');dataset.raise_for_status();catalog=dataset.json()['rows']
            with SessionLocal() as db:
                stored=db.scalar(select(DatasetComparison).where(DatasetComparison.case_id==caseid));state=copy.deepcopy(stored.payload) if stored else {}
                doc_types={r['Document ID']:db.get(Document,r['Document ID']).doc_type for r in items}
            sample=samples[items[0]['Customer']]
            if state.get('sample_id') not in (None,sample):raise ValueError(f'Case {caseid} has a different selected sample; reference edits were not applied.')
            edits={};documents=copy.deepcopy(state.get('documents',{}))
            for row in items:
                candidates=[d for d in catalog if d.get('field')==row['Profile Field Key'] and d['document_type']==doc_types[row['Document ID']]]
                available=[d for d in candidates if d['document_available'].get(sample)]
                if available:candidates=available
                if len(candidates)>1:
                    chosen=[d for d in candidates if documents.get(str(d['section']))==row['Document ID']]
                    if chosen:candidates=chosen
                if len(candidates)!=1:
                    log.append({'action':'reference_workbook_only','excel_row':row['excel_row'],'reason':'No unique available dataset section; reference is preserved in the reviewed workbook.'});continue
                reference=candidates[0]
                value=row['approved_reference']
                if reference['kind']=='number' and row['Profile Field Key']=='charges':
                    # This dataset row is amount-only; the reviewer sheet's field combines method and fee.
                    log.append({'action':'reference_workbook_only','excel_row':row['excel_row'],'reason':'Dataset section stores numeric fee only, while the reviewed field includes selected payment method.'});continue
                old=state.get('edits',{}).get(reference['id'],{}).get('value',reference['values'].get(sample))
                if old!=value:edits[reference['id']]=value
                documents[str(reference['section'])]=row['Document ID']
                log.append({'action':'reference_correction','excel_row':row['excel_row'],'case_id':caseid,'dataset_row':reference['id'],'old_value':old,'new_value':value,'reason':row['reference_reason']+' '+row['How to Solve It']})
            if edits:
                response=c.put(f'/api/cases/{caseid}/comparison',json={'expected_revision':state.get('revision',0),'sample_id':sample,'documents':documents,'edits':edits,'reason':'Reviewer workbook corrections: preserve explicitly accepted extraction values. Original reference values remain in audit history.'})
                response.raise_for_status()
    return log

if __name__=='__main__':
    rows=plan(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')))
    result=apply(rows);Path(sys.argv[2]).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'logged_actions':len(result)}))
