import copy

import pytest
from pydantic import ValidationError

from app.configuration.identity import IdentityPolicy, validate_bindings
from app.domain import default_config, validate_config
from app.grouping import identity_conflicts


def configuration(comparison="compatible_initials"):
    schema = {"type": "object", "properties": {
        "holder": {"type": "object", "properties": {
            "name": {"type": ["string", "null"]},
        }},
        "supplier": {"type": "string"},
        "count": {"type": "integer"},
    }}
    return {
        "profiles": {"custom_one": {"schema": schema}, "custom_two": {"schema": schema}},
        "identity_policy": {"comparison": comparison, "bindings": [
            {"profile": profile, "field_path": "holder.name"}
            for profile in ("custom_one", "custom_two")
        ]},
    }


def documents(left="Alex Example", right="Alex E"):
    return [{"id": str(index), "doc_type": profile, "status": "COMPLETED",
             "normalized": {"holder": {"name": name}, "supplier": "Different Supplier"}}
            for index, (profile, name) in enumerate(zip(("custom_one", "custom_two"), (left, right)))]


def test_new_profiles_work_without_source_mapping():
    cfg = configuration()
    assert identity_conflicts(documents(), cfg) == []
    result = identity_conflicts(documents(right="Other Person"), cfg)
    assert result[0]["evidence"]["document_ids"] == ["0", "1"]
    assert result[0]["eligible"] is False


def test_configuration_changes_comparison_behavior():
    assert not identity_conflicts(documents(), configuration())
    assert identity_conflicts(documents(), configuration("exact_tokens"))


def test_supplier_never_used_when_customer_value_missing():
    docs = documents()
    docs[1]["normalized"]["holder"]["name"] = None
    assert not identity_conflicts(docs, configuration())


def test_incomplete_and_unbound_documents_excluded():
    docs = documents(right="Other Person")
    docs[1]["status"] = "EXTRACTING"
    assert not identity_conflicts(docs, configuration())
    docs[1]["status"] = "COMPLETED"
    docs[1]["doc_type"] = "unbound"
    assert not identity_conflicts(docs, configuration())


def test_explicit_empty_bindings_do_not_fall_back_to_legacy():
    cfg = {"profiles": {}, "identity_policy": {"bindings": []}}
    docs = documents()
    for doc, name in zip(docs, ("Alex Example", "Other Person")):
        doc.update(doc_type="ektp", normalized={"name": name})
    assert identity_conflicts(docs)
    assert not identity_conflicts(docs, cfg)


@pytest.mark.parametrize("path", ["missing", "count", "holder.missing"])
def test_missing_or_nontext_field_rejected(path):
    cfg = configuration()
    cfg["identity_policy"]["bindings"][0]["field_path"] = path
    with pytest.raises(ValueError):
        validate_bindings(IdentityPolicy.model_validate(cfg["identity_policy"]), cfg["profiles"])


@pytest.mark.parametrize("change", [
    {"comparison": "fuzzy_guess"},
    {"bindings": [{"profile": "custom_one", "field_path": "holder.name", "role": "supplier"}]},
    {"unexpected": True},
    {"bindings": [{"profile": "custom_one", "field_path": "holder.name"}] * 2},
    {"bindings": [{"profile": "custom_one", "field_path": "holder.name", "schema_path": "supplier"}]},
])
def test_invalid_policy_rejected(change):
    policy = {**configuration()["identity_policy"], **change}
    with pytest.raises(ValidationError):
        IdentityPolicy.model_validate(policy)


def test_publish_validation_checks_bindings():
    cfg = default_config()
    cfg["identity_policy"] = {"bindings": [{"profile": "ektp", "field_path": "not_present"}]}
    with pytest.raises(ValueError, match="Unknown identity field"):
        validate_config(cfg)
    cfg["identity_policy"]["bindings"][0]["field_path"] = "name"
    cfg["identity_policy"]["bindings"][0]["schema_path"] = "name.raw"
    validate_config(cfg)


def test_equivalent_policy_preserves_existing_findings():
    docs = [{"id": "a", "status": "COMPLETED", "doc_type": "ektp", "normalized": {"name": "Alex Example"}},
            {"id": "b", "status": "COMPLETED", "doc_type": "riplay", "normalized": {"customer_name": "Other Person"}}]
    cfg = default_config()
    previous = identity_conflicts(docs, cfg)
    cfg["identity_policy"] = {"bindings": [
        {"profile": "ektp", "field_path": "name", "schema_path": "name.raw"},
        {"profile": "riplay", "field_path": "customer_name", "schema_path": "customer_name.raw"},
    ]}
    assert identity_conflicts(docs, cfg) == previous
    snapshot = copy.deepcopy(cfg)
    identity_conflicts(docs, cfg)
    assert cfg == snapshot


@pytest.mark.parametrize("left,right,conflict", [
    ("A E", "Alex Example", True),
    ("Alex E", "Alex Example", False),
    ("Alex Example", "Alex Other", True),
    ("Alex Example", "alex example", False),
])
def test_matching_safeguards(left, right, conflict):
    assert bool(identity_conflicts(documents(left, right), configuration())) is conflict
