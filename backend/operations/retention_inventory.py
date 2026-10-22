"""Read-only retention candidates. Never deletes documents or reports.
A bank-approved retention period and legal-hold policy are required before purge.
"""
import argparse,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select
from app.db import Case, SessionLocal
parser=argparse.ArgumentParser()
parser.add_argument('--days',type=int,required=True)
parser.add_argument('--organization',required=True)
args=parser.parse_args()
if args.days < 1:parser.error('days must be positive')
with SessionLocal() as db:
    rows=db.scalars(select(Case).where(Case.org==args.organization,Case.status=='FINALIZED',Case.updated_at < time.time()-args.days*86400))
    print(json.dumps({'read_only':True,'legal_holds_not_evaluated':True,'candidates':[{'case_id':c.id,'branch_id':c.branch_id,'reference':c.reference,'last_updated':c.updated_at} for c in rows]},indent=2))
