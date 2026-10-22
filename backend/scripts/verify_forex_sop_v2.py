"""Read-only production-data verification; no extraction, report or review writes."""
import json
from collections import Counter
from sqlalchemy import select
from app.db import SessionLocal, Case, Config
from app.domain import latest_config
from app.case_processing import inputs
from app.transaction_flows import scope_configuration
from app.sop import evaluate
from app.forex_sop import package_summary

with SessionLocal() as db:
    latest=latest_config(db,"sqe")
    previous=db.scalar(select(Config).where(Config.org=="sqe",Config.version==latest.version-1))
    unchanged = {key:previous.payload.get(key)==latest.payload.get(key) for key in latest.payload if key not in {"sop_rules","forex_sop_policy"}} if previous else {}
    changed_rules=[]
    if previous:
        old={r["id"]:r for r in previous.payload["sop_rules"]}
        changed_rules=[r["id"] for r in latest.payload["sop_rules"] if r!=old.get(r["id"])]
    cases=[]
    for case in db.scalars(select(Case).where(Case.org=="sqe").order_by(Case.customer)):
        frozen=inputs(db,case)
        cfg=scope_configuration(frozen["configuration"],case.template)
        rules=[r for r in cfg.get("sop_rules",[]) if r.get("source_ref","").startswith("SOP3:")]
        if not rules: continue
        cfg["sop_rules"]=rules
        findings=evaluate(frozen["documents"],cfg,frozen["case_context"])
        cases.append({"case_id":case.id,"customer":case.customer,"config_version":frozen["config_version"],"package":package_summary(findings)["forex"],"automated_failures":[{"checkpoint":f["source_ref"],"rule":f["rule_id"],"reason":f.get("reason_code"),"message":f["message"]} for f in findings if f["result"]=="FAIL"]})
    result={"published_version":latest.version,"extraction_and_other_settings_unchanged":all(unchanged.values()),"changed_rules":changed_rules,"mode":"read-only automated evaluation; prior visual decisions are not applied in this diagnostic","cases":cases}
    with open("/tmp/forex-sop-v2-verification.json","w",encoding="utf-8") as target:json.dump(result,target,indent=2,ensure_ascii=False)
    print(json.dumps({"published_version":latest.version,"extraction_and_other_settings_unchanged":all(unchanged.values()),"changed_rules":changed_rules,"cases_checked":len(cases),"evaluation_errors":0}))
