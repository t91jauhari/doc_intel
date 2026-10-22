import copy
import json

import pytest

from app.configuration.upgrade_comparisons import propose_upgrade, supported
from app.domain import default_config, validate_config
from app.sop import evaluate
from app.sop_scoring import point_summary
from app.transaction_flows import scope_configuration


def source():
    cfg = default_config()
    # Use an approved existing account-opening source from packaged definitions.
    from pathlib import Path
    from app import account_opening_sop
    rules = json.loads((Path(account_opening_sop.__file__).parent / "config_data/account_opening_rules.json").read_text())
    rule = next(rule for rule in rules if supported(rule))
    # This helper may require Account Opening profile installation; use the
    # always-present eKTP/RIPLAY pair for generic engine compatibility.
    rule = {**rule, "path": "ektp.name", "other_path": "riplay.customer_name",
            "comparison_policy": json.dumps({"kind": "match"})}
    cfg["sop_rules"].append(rule)
    return cfg, rule["id"]


def test_explicit_conversion_preserves_identity_and_order():
    cfg, rule_id = source()
    original = copy.deepcopy(cfg)
    proposal = propose_upgrade(cfg, [rule_id])
    assert cfg == original
    assert proposal["converted_rule_ids"] == [rule_id]
    assert all(rule["id"] != rule_id for rule in proposal["payload"]["sop_rules"])
    assert proposal["payload"]["generic_sop_rules"][0]["id"] == rule_id
    assert proposal["payload"]["rule_order"] == [rule["id"] for rule in cfg["sop_rules"]]
    assert propose_upgrade(proposal["payload"], [rule_id])["converted_rule_ids"] == []


def test_unknown_and_unsupported_selections_rejected():
    cfg, rule_id = source()
    with pytest.raises(ValueError, match="unknown"):
        propose_upgrade(cfg, ["absent"])
    cfg["sop_rules"][-1]["comparison_policy"] = json.dumps({"kind": "match", "identifier": True})
    with pytest.raises(ValueError, match="unsupported"):
        propose_upgrade(cfg, [rule_id])


def test_invalid_rule_order_rejected():
    cfg = default_config()
    cfg["rule_order"] = []
    with pytest.raises(ValueError, match="Rule order"):
        validate_config(cfg)


@pytest.mark.parametrize("name", ["Alex Example", "Other Customer", None])
def test_conversion_preserves_findings_and_scores(name):
    cfg, rule_id = source()
    cfg["templates"]["test_opening"] = {"label": "Test opening", "document_family": "account_opening",
                                       "report_layout": "account_opening", "required": ["ektp", "riplay"]}
    upgraded = propose_upgrade(cfg, [rule_id])["payload"]
    docs = [{"id": "a", "doc_type": "ektp", "status": "COMPLETED", "normalized": {"name": "Alex Example"}},
            {"id": "b", "doc_type": "riplay", "status": "COMPLETED", "normalized": {"customer_name": name}}]
    previous = evaluate(docs, scope_configuration(cfg, "test_opening"), {})
    current = evaluate(docs, scope_configuration(upgraded, "test_opening"), {})
    assert [(f["rule_id"], f["result"], f["category"]) for f in previous] == [(f["rule_id"], f["result"], f["category"]) for f in current]
    assert point_summary(previous) == point_summary(current)
