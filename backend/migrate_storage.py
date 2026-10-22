"""Copy originals from the previous local layout to configured MinIO; keep originals.
Run with API and workers stopped: cd backend && python migrate_storage.py
Existing DATABASE_URL and STORAGE_PATH must refer to the old deployment.
"""

import hashlib
from sqlalchemy import select
from app.db import SessionLocal, Document, Report
from app.settings import settings
from app.storage import store, original_key
from app.reporting import persist_report

if settings.storage_driver != "minio":
    raise SystemExit("Configure STORAGE_DRIVER=minio before migration.")
with SessionLocal() as db:
    for doc in db.scalars(select(Document)):
        source = settings.storage / doc.id / "original.pdf"
        if not source.exists():
            # A previously migrated object must be readable, never silently skipped.
            data = store().read(original_key(doc))
        else:
            data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != doc.sha256:
            raise RuntimeError(f"Original checksum mismatch: {doc.id}")
        key = original_key(doc)
        store().put(key, data, "application/pdf")
        if hashlib.sha256(store().read(key)).hexdigest() != doc.sha256:
            raise RuntimeError(f"Stored checksum mismatch: {doc.id}")
        doc.provider_state = {**doc.provider_state, "storage_key": key}
        db.commit()
        print(f"Verified document {doc.id}")
    for report in db.scalars(select(Report)):
        persist_report(report)
        print(f"Stored report {report.id}")
print("Migration complete. Originals retained locally.")
