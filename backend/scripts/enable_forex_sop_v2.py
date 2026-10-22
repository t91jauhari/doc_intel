"""Publish executable Forex policies without changing extraction settings."""
import copy
import json
import sys

from app.db import Config, SessionLocal
from app.domain import audit, validate_config
from app.forex_sop import effective_rule, policy_for
from app.profile_guidance import locked_latest_config

org = sys.argv[1] if len(sys.argv) > 1 else "sqe"
with SessionLocal.begin() as db:
    latest = locked_latest_config(db, org)
    payload = copy.deepcopy(latest.payload)
    payload["sop_rules"] = [effective_rule(r) for r in payload["sop_rules"]]
    payload["forex_sop_policy"] = policy_for(payload)
    # Publish only the SOP contract. Profiles, schemas, provider and flows stay intact.
    if payload != latest.payload:
        validate_config(payload)
        saved = Config(org=org, version=latest.version + 1, payload=payload, published_by="system.forex-sop-v2")
        db.add(saved)
        db.flush()
        audit(db, org, "system", "config.forex_sop_v2_enabled", version=saved.version, previous_version=latest.version)
    else:
        saved = latest
    print(json.dumps({"organization":org,"version":saved.version,"changed":saved.id != latest.id}))
