"""Publish newly supported profiles and automation configuration; preserve all case-pinned historical configs.
Run with API/workers stopped: cd backend && python migrate_profiles.py
Development startup does this automatically for its development organization.
"""

from sqlalchemy import select
from app.db import SessionLocal, Config, Base, engine
from app.domain import upgrade_profiles

Base.metadata.create_all(engine)

with SessionLocal.begin() as db:
    for org in db.scalars(select(Config.org).distinct()):
        print(org, "upgraded" if upgrade_profiles(db, org) else "already current")
