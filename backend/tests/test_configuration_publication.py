import copy
from dataclasses import replace

import pytest
from sqlalchemy import func, select

from app import main
from app.configuration import publication
from app.configuration.store import ConfigurationBase, Publication, compile_publication, fingerprint
from app.db import Audit, Case, Config, SessionLocal, engine


@pytest.fixture
def dual(signed, monkeypatch):
    ConfigurationBase.metadata.drop_all(engine)
    ConfigurationBase.metadata.create_all(engine)
    monkeypatch.setattr(main, "settings", replace(main.settings, configuration_storage_mode="dual"))
    try:
        yield signed
    finally:
        ConfigurationBase.metadata.drop_all(engine)


def test_dual_publish_matches_source_and_preserves_history(dual):
    current = dual.get("/api/config").json()
    payload = copy.deepcopy(current["payload"])
    payload["report_title"] = "Updated report title"
    with SessionLocal.begin() as db:
        pinned = Case(org="sqe", branch_id="synthetic", reference="pinned", customer="Synthetic",
                      template="forex", created_by="synthetic", config_id=current["id"])
        db.add(pinned)
        db.flush()
        case_id = pinned.id
    result = dual.post("/api/config/publish", json={"expected_version": current["version"], "payload": payload})
    assert result.status_code == 200, result.text
    saved = result.json()
    assert saved["version"] == current["version"] + 1
    with SessionLocal() as db:
        original = db.get(Config, current["id"])
        assert original.payload["report_title"] == current["payload"]["report_title"]
        normalized = db.get(Publication, saved["publication_id"])
        assert normalized.source_config_id == saved["id"]
        assert compile_publication(db, normalized) == saved["payload"]
        assert db.scalar(select(func.count()).select_from(Publication)) == 1
        assert db.get(Case, case_id).config_id == current["id"]
    stale = dual.post("/api/config/publish", json={"expected_version": current["version"], "payload": payload})
    assert stale.status_code == 409
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Publication)) == 1


def test_dual_publish_missing_schema_fails_without_creating_tables(dual):
    current = dual.get("/api/config").json()
    ConfigurationBase.metadata.drop_all(engine)
    result = dual.post("/api/config/publish", json={"expected_version": current["version"], "payload": current["payload"]})
    assert result.status_code == 503
    assert dual.get("/api/config").json()["version"] == current["version"]


@pytest.mark.parametrize("failure_point", ["import_publication", "compile_publication"])
def test_normalized_write_failure_rolls_back_legacy_revision(dual, monkeypatch, failure_point):
    current = dual.get("/api/config").json()
    with SessionLocal() as db:
        count = db.scalar(select(func.count()).select_from(Config))
        audits = db.scalar(select(func.count()).select_from(Audit))

    def fail(*args, **kwargs):
        raise ValueError("Simulated normalized import failure")

    monkeypatch.setattr(publication, failure_point, fail)
    result = dual.post("/api/config/publish", json={"expected_version": current["version"], "payload": current["payload"]})
    assert result.status_code == 422
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Config)) == count
        assert db.scalar(select(func.count()).select_from(Publication)) == 0
        assert db.scalar(select(func.count()).select_from(Audit)) == audits


def test_publication_service_does_not_mutate_input(dual):
    current = dual.get("/api/config").json()
    payload = copy.deepcopy(current["payload"])
    payload["profiles"]["ektp"].pop("system_instruction", None)
    source_hash = fingerprint(payload)
    with SessionLocal.begin() as db:
        result = publication.publish_configuration(db, organization="sqe", actor="synthetic",
            expected_version=current["version"], payload=payload, storage_mode="dual")
        assert result["publication_id"]
        assert result["payload"]["profiles"]["ektp"]["system_instruction"]
    assert fingerprint(payload) == source_hash


def test_legacy_publish_does_not_require_new_tables(signed):
    current = signed.get("/api/config").json()
    result = signed.post("/api/config/publish", json={"expected_version": current["version"], "payload": current["payload"]})
    assert result.status_code == 200, result.text
    assert "publication_id" not in result.json()
