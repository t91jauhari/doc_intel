"""Read-only export preview using real stored reports; no processing or report writes."""
from pathlib import Path
import sys
from sqlalchemy import select
from app.db import SessionLocal,Case,Report
from app.branch_report import select_branch_reports,export_period
from app.kertas_kerja import workbook
with SessionLocal() as db:
    case=db.get(Case,"2c9a2036-8606-40a4-9b3d-0d3b21867d2f")
    reports=db.scalars(select(Report).where(Report.org==case.org,Report.branch_id==case.branch_id).order_by(Report.case_id,Report.version.desc())).all()
    current=select_branch_reports(db,reports,"forex")
    snapshots=[{**r.snapshot,"release_state":r.state,"snapshot_hash":r.fingerprint,"report_export_context":{"period":export_period(None,None)}} for r in current.values()]
    Path(sys.argv[1] if len(sys.argv)>1 else "/preview/Branch-Kertas-Kerja.xlsx").write_bytes(workbook(snapshots))
    print({"customers":len(snapshots),"preview":"Branch-Kertas-Kerja.xlsx","source_reports_changed":False})
