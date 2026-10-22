from sqlalchemy import func, select

from app.configuration.store import fingerprint
from app.db import Config, SessionLocal, User


def test_preview_is_read_only_and_preserves_version(signed):
    current = signed.get("/api/config").json()
    candidates = signed.get("/api/config/upgrades/comparisons").json()
    assert candidates["version"] == current["version"]
    assert candidates["candidates"]
    rule_id = candidates["candidates"][0]["id"]
    with SessionLocal() as db:
        count = db.scalar(select(func.count()).select_from(Config))
        source = fingerprint(db.get(Config, current["id"]).payload)
    result = signed.post("/api/config/upgrades/comparisons/preview", json={
        "expected_version": current["version"], "rule_ids": [rule_id],
    })
    assert result.status_code == 200, result.text
    assert result.json()["converted_rule_ids"] == [rule_id]
    assert result.json()["activated"] is False
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Config)) == count
        assert fingerprint(db.get(Config, current["id"]).payload) == source


def test_preview_rejects_stale_and_invalid_selection(signed):
    current = signed.get("/api/config").json()
    endpoint = "/api/config/upgrades/comparisons/preview"
    assert signed.post(endpoint, json={"expected_version": current["version"] + 1,
                                       "rule_ids": ["not_present"]}).status_code == 409
    assert signed.post(endpoint, json={"expected_version": current["version"],
                                       "rule_ids": ["not_present"]}).status_code == 422
    assert signed.post(endpoint, json={"expected_version": current["version"],
                                       "rule_ids": []}).status_code == 422


def test_nonadministrator_cannot_preview(signed):
    with SessionLocal.begin() as db:
        user = db.scalar(select(User).where(User.email == "sqe@bic.local"))
        user.role = "reviewer"
    assert signed.get("/api/config/upgrades/comparisons").status_code == 403
    assert signed.get("/api/config/upgrades/compatibility").status_code == 403
    assert signed.post("/api/config/upgrades/comparisons/fields", json={
        "expected_version": 1, "family": "forex",
    }).status_code == 403
    assert signed.post("/api/config/upgrades/compatibility/preview", json={
        "expected_version": 1, "selected_keys": ["sop_review_bypass"],
    }).status_code == 403
    assert signed.post("/api/config/upgrades/comparisons/preview", json={
        "expected_version": 1, "rule_ids": ["anything"],
    }).status_code == 403


def test_compatibility_preview_is_explicit_and_read_only(signed):
    from app.configuration.compatibility import release_definition

    current = signed.get("/api/config").json()
    assert signed.get("/api/config/upgrades/compatibility").status_code == 200
    legacy = current["payload"]
    keys = list(release_definition()["defaults"])
    for key in keys:
        legacy.pop(key)
    before = signed.get("/api/config").json()
    result = signed.post("/api/config/upgrades/compatibility/preview", json={
        "expected_version": current["version"], "selected_keys": keys, "payload": legacy,
    })
    assert result.status_code == 200, result.text
    assert result.json()["activated"] is False
    assert result.json()["payload"]["sop_review_bypass"] is False
    assert signed.get("/api/config").json() == before
    assert signed.post("/api/config/upgrades/compatibility/preview", json={
        "expected_version": current["version"] + 1, "selected_keys": keys, "payload": legacy,
    }).status_code == 409


def test_field_catalog_is_family_scoped_read_only_and_versioned(signed):
    current = signed.get("/api/config").json()
    endpoint = "/api/config/upgrades/comparisons/fields"
    result = signed.post(endpoint, json={"expected_version": current["version"], "family": "forex"})
    assert result.status_code == 200, result.text
    fields = result.json()["fields"]
    assert any(field["path"] == "ektp.name" and field["schema_path"] == "ektp.name.raw" for field in fields)
    assert not any(field["profile"] == "account_opening_form" for field in fields)
    assert signed.get("/api/config").json() == current
    assert signed.post(endpoint, json={"expected_version": current["version"] + 1, "family": "forex"}).status_code == 409
    assert signed.post(endpoint, json={"expected_version": current["version"], "family": "unknown"}).status_code == 422
