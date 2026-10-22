import copy

import pytest
from pydantic import ValidationError

from app.configuration.comparison import ComparisonPolicy, evaluate_comparison
from app.configuration.rule_scope import validate_rule_scope
from app.domain import default_config, validate_config
from app.transaction_flows import scope_configuration


def scoped_config():
    cfg = default_config()
    cfg["rule_scope"] = {"family_rule_ids": {"forex": [], "account_opening": []}}
    return cfg


def test_explicit_scope_does_not_depend_on_source_text():
    cfg = scoped_config()
    rule = copy.deepcopy(cfg["sop_rules"][0])
    rule.update(id="custom_rule", source_ref="An arbitrary source title")
    cfg["sop_rules"].append(rule)
    cfg["rule_scope"]["family_rule_ids"]["forex"] = [rule["id"]]
    flow = next(iter(cfg["templates"]))
    cfg["templates"][flow].update(document_family="forex")
    cfg["templates"][flow].pop("sop_rule_ids", None)
    result = scope_configuration(cfg, flow)
    assert [item["id"] for item in result["sop_rules"]] == ["custom_rule"]
    cfg["templates"][flow]["sop_rule_ids"] = []
    assert scope_configuration(cfg, flow)["sop_rules"] == []


def test_scope_is_checked_by_publication_validation():
    cfg = scoped_config()
    validate_config(cfg)
    cfg["rule_scope"]["family_rule_ids"]["forex"] = ["nonexistent_rule"]
    with pytest.raises(ValueError, match="unknown SOP"):
        validate_config(cfg)


@pytest.mark.parametrize("mapping", [
    {"forex": []},
    {"forex": ["missing"], "account_opening": []},
    {"forex": [], "account_opening": [], "unknown_family": []},
])
def test_invalid_scope_rejected(mapping):
    cfg = scoped_config()
    cfg["rule_scope"]["family_rule_ids"] = mapping
    with pytest.raises(ValueError):
        validate_rule_scope(cfg)


def docs(left="0012345678901234", right="0012345678901234"):
    return [{"doc_type": profile, "status": "COMPLETED", "normalized": {"identity": value}}
            for profile, value in (("custom_a", left), ("custom_b", right))]


def policy(**changes):
    return ComparisonPolicy(left="custom_a.identity", right="custom_b.identity", **changes)


def test_digit_constraint_preserves_leading_zeros():
    assert evaluate_comparison(docs(), policy(pattern="[0-9]{16}")).result == "PASS"
    assert evaluate_comparison(docs("123", "123"), policy(pattern="[0-9]{16}")).reason == "invalid_format"


@pytest.mark.parametrize("value", [None, "", "  ", 123])
def test_missing_values_do_not_pass(value):
    assert evaluate_comparison(docs(value, value), policy()).result == "FAIL"


def test_duplicate_completed_document_fails():
    documents = docs()
    documents.append(copy.deepcopy(documents[0]))
    assert evaluate_comparison(documents, policy()).reason == "ambiguous"


def test_normalization_is_explicit():
    documents = docs("Alex   Example", "alex example")
    assert evaluate_comparison(documents, policy()).result == "FAIL"
    assert evaluate_comparison(documents, policy(normalization="casefold_whitespace")).result == "PASS"


def test_arbitrary_regex_is_rejected():
    with pytest.raises(ValidationError):
        policy(pattern="(a+)+$")
