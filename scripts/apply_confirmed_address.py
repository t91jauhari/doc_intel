"""One explicit reviewer-confirmed glyph correction; raw model observation remains intact."""
import json,re,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.db import SessionLocal,Document
from reviewer_field_cycle import client

if __name__=='__main__':
    if len(sys.argv)!=3 or sys.argv[1]!='Al':raise SystemExit('This operation requires the explicitly confirmed Al prefix and an output log path.')
    docid='899de05f-caf4-47d9-941e-39629950c338';field='beneficiary_address'
    with SessionLocal() as db:
        doc=db.get(Document,docid);before=doc.normalized[field]
        if not isinstance(before,dict) or not isinstance(before.get('raw'),str):raise ValueError('Unexpected address structure; correction was not applied.')
        after={**before,'raw':re.sub(r'^A1(?=[,\s])','Al',before['raw'])}
    reason='User explicitly confirmed: Use Al (letter L), as in the reference. Correct only this leading unit character. Postal code and all remaining original-page text were verified by enlarged reread. Preserve raw extraction and record reviewer correction.'
    with client() as c:
        if after!=before:
            response=c.post(f'/api/documents/{docid}/effective-corrections',json={'field':field,'expected_value':before,'value':after,'reason':reason});response.raise_for_status()
    for _ in range(60):
        with SessionLocal() as db:
            current=db.get(Document,docid)
            if current.status=='COMPLETED' and current.normalized[field]==after:break
        time.sleep(2)
    else:raise RuntimeError('Correction was submitted but completion is not confirmed.')
    log={'document_id':docid,'field':field,'before':before,'after':after,'reason':reason,'raw_extraction_preserved':True}
    Path(sys.argv[2]).write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8');print('Confirmed Al address correction applied and revalidated.')
