"""Offline complete database + referenced private-object backup.
Stop API/workers before running. Does not change production data.
python operations/backup.py --destination /secure/backups/run-YYYYMMDD
"""
import argparse, hashlib, json, os, sqlite3, subprocess, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select
from app.db import engine, SessionLocal, Document, Report
from app.storage import original_key, store
from app.reporting import report_key
from app.field_evidence import evidence_images

parser=argparse.ArgumentParser()
parser.add_argument("--destination",required=True)
args=parser.parse_args()
os.umask(0o077)
path=Path(args.destination).resolve()
path.mkdir(parents=True,exist_ok=False)
url=engine.url
if url.get_backend_name()=="sqlite":
    with sqlite3.connect(url.database) as source, sqlite3.connect(path/"database.sqlite") as target:
        source.backup(target)
elif url.get_backend_name()=="postgresql":
    environment={**os.environ,"PGPASSWORD":url.password or ""}
    command=["pg_dump","--format=custom","--file",str(path/"database.dump"),"--host",url.host or "localhost","--port",str(url.port or 5432),"--username",url.username or "",url.database]
    subprocess.run(command,env=environment,check=True)
else:
    raise RuntimeError("Unsupported database backup driver")
keys=set()
with SessionLocal() as db:
    for doc in db.scalars(select(Document)):
        keys.add(original_key(doc))
        if doc.provider_state.get("parse_response_key"):
            keys.add(doc.provider_state["parse_response_key"])
        keys.update(e["storage_key"] for e in evidence_images(doc.validation) if e.get("available"))
    for report in db.scalars(select(Report)):
        formats=next((x["parameters"].get("formats",[]) for x in report.snapshot.get("configuration",{}).get("workflow",[]) if x["action"]=="render_report"),["pdf","xlsx"])
        keys.update(report_key(report,fmt) for fmt in {"json",*formats})
        for doc in report.snapshot.get("documents",[]):
            parse_key = doc.get("provider_state", {}).get("parse_response_key")
            if parse_key: keys.add(parse_key)
            keys.update(e["storage_key"] for e in evidence_images(doc.get("validation",{})) if e.get("available"))
manifest=[]
for key in sorted(keys):
    content=store().read(key)
    target=path/"objects"/key
    if not target.resolve().is_relative_to(path):raise ValueError("Invalid object key")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(content)
    manifest.append({"key":key,"sha256":hashlib.sha256(content).hexdigest(),"bytes":len(content)})
(path/"manifest.json").write_text(json.dumps({"database_driver":url.get_backend_name(),"objects":manifest},indent=2),encoding="utf-8")
print("Backup complete:",len(manifest),"referenced objects. Verify a restore in isolation before relying on it.")
