import copy

import pytest
from sqlalchemy import select

from app.db import Case, Config, SessionLocal, User
from app.domain import default_config, validate_config
from app.schema_descriptions import contract, with_schemas
from test_platform import upload


def test_descriptions_edit_all_nested_nodes_without_changing_contract():
    config = default_config()
    original = copy.deepcopy(config)
    config["profiles"]["ektp"]["schema"]["properties"]["name"]["description"] = "Read only the complete printed customer name."
    config["profiles"]["ektp"]["schema"]["properties"]["name"]["properties"]["raw"]["description"] = "Preserve all visible characters; null when unreadable."
    config["profiles"]["riplay"]["schema"]["properties"]["page_initials"]["properties"]["pages"]["items"]["properties"]["evidence"]["description"] = "Describe the bottom-right agreement mark on this physical page."
    validate_config(config)
    assert contract(config["profiles"]["ektp"]["schema"]) == contract(original["profiles"]["ektp"]["schema"])
    assert config["profiles"]["ektp"]["schema_version"] == original["profiles"]["ektp"]["schema_version"]
    for change in ["type", "required", "extra"]:
        bad = copy.deepcopy(config)
        bad['provider']='fixture'
        schema = bad["profiles"]["ektp"]["schema"]
        if change == "type":
            schema["properties"]["nik"]["type"] = "number"
        elif change == "required":
            schema["required"].remove("nik")
        else:
            schema["properties"]["new_field"] = {"type": "string", "description": "Unregistered field"}
        with pytest.raises(ValueError):
            validate_config(bad)
    for value in [None, " ", 10, "x" * 20001]:
        bad = copy.deepcopy(config)
        bad["profiles"]["ektp"]["schema"]["properties"]["nik"]["description"] = value
        with pytest.raises(ValueError, match="field description"):
            validate_config(bad)


def test_legacy_profile_schemas_are_supplied_without_mutating_storage():
    config = default_config()
    defaults = copy.deepcopy(config["profiles"])
    del config["profiles"]["ektp"]["schema"]
    materialized = with_schemas(config, defaults)
    assert materialized["profiles"]["ektp"]["schema"] == defaults["ektp"]["schema"]
    assert "schema" not in config["profiles"]["ektp"]


def test_publish_descriptions_is_versioned_and_existing_cases_remain_pinned(signed):
    before = upload(signed, names=("First Customer_ektp.pdf",), key="description-before").json()["case_ids"][0]
    current = signed.get("/api/config").json()
    original = copy.deepcopy(current["payload"])
    edited = copy.deepcopy(original)
    edited["profiles"]["ektp"]["schema"]["properties"]["name"]["description"] = "Extract the customer name from the printed identity name row only."
    saved = signed.post("/api/config/publish", json={"expected_version": current["version"], "payload": edited})
    assert saved.status_code == 200, saved.text
    assert signed.get("/api/config").json()["payload"]["profiles"]["ektp"]["schema"] == edited["profiles"]["ektp"]["schema"]
    after = upload(signed, names=("Second Customer_ektp.pdf",), key="description-after").json()["case_ids"][0]
    with SessionLocal() as db:
        old = db.get(Config, db.get(Case, before).config_id)
        new = db.get(Config, db.get(Case, after).config_id)
        assert old.payload["profiles"]["ektp"]["schema"] == original["profiles"]["ektp"]["schema"]
        assert new.id == saved.json()["id"]
        assert new.payload["profiles"]["ektp"]["system_prompt"] == original["profiles"]["ektp"]["system_prompt"]
    user = signed.get("/api/auth/session").json()["user"]
    with SessionLocal.begin() as db:
        db.get(User, user["id"]).role = "auditor"
    assert signed.get("/api/config").json()["can_edit"] is False
    assert signed.post("/api/config/publish", json={"expected_version": saved.json()["version"], "payload": edited}).status_code == 403
