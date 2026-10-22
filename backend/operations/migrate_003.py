"""Additive migration: run explicitly with API/workers stopped.
Existing document/case/config records are preserved. No downgrade/drop action.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select
from app.db import Base, engine, Config, SessionLocal
from app.domain import upgrade_profiles
Base.metadata.create_all(engine)
with SessionLocal.begin() as db:
    for org in db.scalars(select(Config.org).distinct()):
        upgrade_profiles(db, org)
print('Additive schema and versioned profile migration completed.')
