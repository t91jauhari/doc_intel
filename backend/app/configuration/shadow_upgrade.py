"""Generate explicit proposals in memory and verify complete saved-case scores."""
import argparse
import json
import os
from collections import Counter

from sqlalchemy import create_engine, text

from .upgrade_comparisons import propose_upgrade, supported


def verify_records(records):
    from app.sop import evaluate
    from app.sop_scoring import point_summary
    from app.transaction_flows import scope_configuration, score_configuration

    outcomes, converted, cases, mismatches = 0, 0, 0, 0
    blocked = Counter()
    for record in records:
        payload = record["configuration"]
        selected = [rule["id"] for rule in payload.get("sop_rules", []) if supported(rule)]
        if not selected:
            continue
        try:
            proposal = propose_upgrade(payload, selected)
        except ValueError as exc:
            blocked[str(exc)] += 1
            continue
        draft = proposal["payload"]
        before_cfg = scope_configuration(payload, record["template"])
        after_cfg = scope_configuration(draft, record["template"])
        before = evaluate(record["documents"], before_cfg, record["context"])
        after = evaluate(record["documents"], after_cfg, record["context"])
        before_states = [(r["rule_id"], r["result"], r.get("eligible"), r.get("category")) for r in before]
        after_states = [(r["rule_id"], r["result"], r.get("eligible"), r.get("category")) for r in after]
        if (before_states != after_states or point_summary(before) != point_summary(after)
                or score_configuration(payload, record["template"], before)
                != score_configuration(draft, record["template"], after)):
            mismatches += 1
        cases += 1
        outcomes += len(before)
        converted += len(proposal["converted_rule_ids"])
    return {"cases_checked": cases, "ordered_findings_checked": outcomes,
            "rule_conversions_across_case_versions": converted,
            "case_or_score_mismatches": mismatches,
            "blocked_cases": sum(blocked.values()), "blockers": dict(blocked), "activated": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-database", required=True)
    args = parser.parse_args()
    engine = create_engine(os.environ["REFACTOR_DATABASE_URL"])
    try:
        with engine.begin() as connection:
            if connection.scalar(text("SELECT current_database()")) != args.expected_database:
                raise ValueError("Unexpected database.")
        with engine.begin() as connection:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            records = []
            for case in connection.execute(text(
                "SELECT c.id,c.template,cfg.payload,ctx.payload AS context FROM cases c "
                "JOIN configurations cfg ON cfg.id=c.config_id LEFT JOIN case_contexts ctx ON ctx.case_id=c.id"
            )).mappings():
                docs = [dict(row) for row in connection.execute(text(
                    "SELECT id,doc_type,status,normalized,validation FROM documents WHERE case_id=:id ORDER BY created_at"
                ), {"id": case["id"]}).mappings()]
                records.append({"configuration": case["payload"], "template": case["template"],
                                "documents": docs, "context": case["context"] or {}})
            result = verify_records(records)
        print(json.dumps(result))
        if not result["cases_checked"] or result["case_or_score_mismatches"]:
            raise SystemExit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
