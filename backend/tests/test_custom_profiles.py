import copy
from types import SimpleNamespace

import pytest

from app.configuration.profiles import schema_report, validate_shape
from app.domain import default_config, validate_config
from test_platform import upload, process_all


def configured(payload=None):
    cfg = copy.deepcopy(payload) if payload is not None else default_config()
    cfg["provider"] = "llama"
    cfg["profiles"]["custom_note"] = {
        "label": "Custom note", "validation_adapter": "schema", "policy": {},
        "classification_description": "A synthetic custom note with two printed names.",
        "parse_prompt": "Read the two name boxes.", "system_prompt": "Extract only the visible names.",
        "suffixes": ["customnote"],
        "schema": {"type": "object", "properties": {
            "name": {"type": ["string", "null"], "description": "First printed name."},
            "confirmation": {"type": ["string", "null"], "description": "Confirmation name."}},
            "required": ["name", "confirmation"]},
        "columns": [["name", "Name"], ["confirmation", "Confirmation"]],
    }
    cfg.setdefault("document_families", {})["custom"] = {"label": "Custom", "profiles": ["custom_note"]}
    cfg.setdefault("generic_sop_rules", []).append({"id": "custom_names_match", "label": "Printed names match",
        "families": ["custom"], "policy": {"left": "custom_note.name", "right": "custom_note.confirmation"}})
    if "rule_order" in cfg:
        cfg["rule_order"].append("custom_names_match")
    cfg["templates"]["custom"] = {"label": "Custom", "document_family": "custom", "required": ["custom_note"],
        "sop_rule_ids": ["custom_names_match"], "enabled": True, "dataset_id": None, "report_layout": "forex"}
    return cfg


def test_custom_profile_schema_and_adapter_are_explicit():
    cfg = configured()
    validate_config(cfg)
    cfg["profiles"]["custom_note"].pop("validation_adapter")
    with pytest.raises(ValueError, match="schema validation adapter"):
        validate_config(cfg)


def test_custom_profiles_reject_unenforced_schema_constraints():
    cfg = configured()
    cfg["profiles"]["custom_note"]["schema"]["properties"]["name"]["pattern"] = "[A-Z]+"
    with pytest.raises(ValueError, match="business checks as SOP"):
        validate_config(cfg)


def test_custom_profiles_reject_ignored_policy_and_nonfinite_values():
    cfg = configured()
    cfg["profiles"]["custom_note"]["policy"]["minimum_age"] = 18
    with pytest.raises(ValueError, match="business policy as SOP"):
        validate_config(cfg)
    with pytest.raises(ValueError, match="finite JSON"):
        validate_shape(float("nan"), {"type": "number"})
    validate_shape(7, {"type": "integer"})


def test_custom_profile_id_matches_document_storage_length():
    cfg = configured()
    cfg["profiles"]["c" * 51] = copy.deepcopy(cfg["profiles"]["custom_note"])
    with pytest.raises(ValueError, match="at most 50"):
        validate_config(cfg)


def test_schema_projection_checks_types_missing_values_and_unexpected_keys():
    cfg = configured()
    doc = SimpleNamespace(doc_type="custom_note", overrides={})
    report = schema_report(doc, cfg, {"extract_result": {"name": "Example", "confirmation": None}})
    assert report["status"] == "FAIL" and report["fields"]["confirmation"]["status"] == "FAIL"
    for value in ({"name": 7, "confirmation": "Example"}, {"name": "Example"},
                  {"name": "Example", "confirmation": "Example", "unconfigured": "x"}):
        with pytest.raises(ValueError):
            schema_report(doc, cfg, {"extract_result": value})


def test_custom_profile_runs_upload_extraction_sop_and_report(signed, monkeypatch):
    current = signed.get("/api/config").json()
    cfg = configured(current["payload"])
    saved = signed.post("/api/config/publish", json={"expected_version": current["version"], "payload": cfg})
    assert saved.status_code == 200, saved.text
    assert signed.get("/api/config").json()["payload"]["profiles"]["custom_note"]["schema"] == cfg["profiles"]["custom_note"]["schema"]
    monkeypatch.setattr("app.processor.run_provider", lambda doc, payload, heartbeat:
        ({"extract_result": {"name": "Example", "confirmation": "Example"}, "extract_metadata": {}},
         {"type": "custom_note", "method": "synthetic", "confirmed": True}))
    uploaded = upload(signed, names=("Synthetic_customnote.pdf",), template="custom", key="custom-profile")
    assert uploaded.status_code == 202, uploaded.text
    process_all()
    case = signed.get("/api/cases/" + uploaded.json()["case_ids"][0]).json()
    assert case["documents"][0]["doc_type"] == "custom_note"
    assert case["documents"][0]["status"] == "COMPLETED", case["documents"][0].get("error")
    assert case["documents"][0]["validation"]["processing_mode"] == "configured_schema"
    findings = case["reports"][0]["snapshot"]["findings"]
    assert next(item for item in findings if item["rule_id"] == "custom_names_match")["result"] == "PASS"
    monkeypatch.setattr("app.field_reprocessing.extract_selected", lambda doc, request, heartbeat: {"name": "Updated name"})
    instruction = "Read the full printed name from the first name box."
    retried = signed.post("/api/documents/" + case["documents"][0]["id"] + "/reprocess-fields",
        json={"fields": ["name"], "reason": "Check printed name", "instruction": instruction})
    assert retried.status_code == 202, retried.text
    assert retried.json()["guidance_saved_to_profile"]
    from app.processor import process_job
    process_job(retried.json()["job_id"])
    process_all()
    refreshed = signed.get("/api/cases/" + case["id"]).json()
    assert refreshed["documents"][0]["normalized"]["name"] == "Updated name"
    assert refreshed["documents"][0]["normalized"]["confirmation"] == "Example"
    profile = signed.get("/api/config").json()["payload"]["profiles"]["custom_note"]
    assert instruction in profile["system_instruction"]
