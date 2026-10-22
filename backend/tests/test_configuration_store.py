"""Synthetic-only storage contract tests; no provider or operational database."""
import json

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.configuration.store import (
    ConfigurationBase, ConfigurationEntry, Publication,
    compile_publication, import_publication,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    ConfigurationBase.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def sample():
    return {
        "profiles": {"custom": {"schema": {"type": "object"}, "system_prompt": "Visible text only"}},
        "document_families": {"new_family": {"profiles": ["custom"]}},
        "templates": {}, "sop_rules": [{"id": "second"}, {"id": "first"}],
        "unknown_future_extension": {"value": [None, "é", 12]},
    }


def load(db, payload=None, organization="test"):
    return import_publication(db, organization=organization, revision=1,
                              source_config_id="synthetic", payload=sample() if payload is None else payload)


def test_round_trip_preserves_order_extensions_and_empty_sections(db):
    payload = sample()
    publication = load(db, payload)
    assert compile_publication(db, publication) == payload
    assert "profile_variants" not in compile_publication(db, publication)
    assert [r["id"] for r in compile_publication(db, publication)["sop_rules"]] == ["second", "first"]


def test_idempotent_and_organization_scoped(db):
    first = load(db)
    assert load(db).id == first.id
    assert load(db, organization="other").id != first.id


def test_rewrite_rejected(db):
    load(db)
    with pytest.raises(ValueError, match="cannot be replaced"):
        load(db, {"profiles": {}})


def test_persisted_tampering_detected(db):
    publication = load(db)
    entry = db.scalar(select(ConfigurationEntry).where(ConfigurationEntry.section == "profiles"))
    entry.value = {"tampered": True}
    db.flush()
    with pytest.raises(ValueError, match="integrity"):
        compile_publication(db, publication)


def test_caller_controls_rollback(db):
    load(db)
    db.rollback()
    assert db.scalar(select(Publication)) is None


@pytest.mark.parametrize("payload", [{"profiles": []}, {"sop_rules": {}}, {"profiles": {"bad": 1}}])
def test_invalid_structure_rejected_before_writes(db, payload):
    with pytest.raises(ValueError):
        load(db, payload)
    assert db.scalar(select(Publication)) is None


def test_returned_payload_does_not_mutate_storage(db):
    publication = load(db)
    compiled = compile_publication(db, publication)
    compiled["profiles"].clear()
    assert "custom" in compile_publication(db, publication)["profiles"]


def test_existing_application_defaults_round_trip(db):
    from app.domain import default_config

    # Match the existing JSON database contract (Python tuples become arrays).
    payload = json.loads(json.dumps(default_config()))
    publication = load(db, payload)
    assert compile_publication(db, publication) == payload
