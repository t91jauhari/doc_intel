"""Publish spatial instructions once for an existing organization's profiles."""
import copy
import json
import sys

from app.db import Config, SessionLocal
from app.domain import audit, validate_config
from app.extraction_prompts import system_instruction
from app.profile_guidance import locked_latest_config

org = sys.argv[1] if len(sys.argv) > 1 else "sqe"
with SessionLocal.begin() as db:
    latest = locked_latest_config(db, org)
    payload = copy.deepcopy(latest.payload)
    changed = []
    for name, profile in payload["profiles"].items():
        instruction = system_instruction(profile)
        if profile.get("system_instruction") != instruction:
            profile["system_instruction"] = instruction
            changed.append(name)
    if changed:
        validate_config(payload)
        saved = Config(org=org, version=latest.version + 1, payload=payload, published_by="system")
        db.add(saved)
        db.flush()
        audit(db, org, "system", "config.spatial_grounding_enabled", version=saved.version,
              previous_version=latest.version, profiles=changed)
    else:
        saved = latest
    print(json.dumps({"organization":org,"version":saved.version,"updated_profiles":changed}))
