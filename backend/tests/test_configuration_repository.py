import copy

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.configuration.repository import ConfigurationIntegrityError, get_revision, resolve_revision
from app.configuration.store import ConfigurationBase, ConfigurationEntry, import_publication
from app.db import Base, Config


@pytest.fixture
def database():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    ConfigurationBase.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        for version, name in [(1, "First"), (2, "Second")]:
            payload = {"profiles": {"synthetic": {"label": name}}}
            record = Config(id=str(version), org="synthetic", version=version,
                            payload=payload, published_by="synthetic")
            session.add(record)
            session.flush()
            import_publication(session, organization=record.org, revision=version,
                               source_config_id=record.id, payload=copy.deepcopy(payload))
        yield session
    engine.dispose()


@pytest.mark.parametrize("mode", ["legacy", "verify", "normalized"])
def test_old_case_pin_never_resolves_to_latest(database, mode):
    snapshot = get_revision(database, "1", read_mode=mode)
    assert snapshot.id == "1" and snapshot.version == 1
    assert snapshot.payload["profiles"]["synthetic"]["label"] == "First"
    snapshot.payload["profiles"]["synthetic"]["label"] = "Caller edit"
    assert database.get(Config, "1").payload["profiles"]["synthetic"]["label"] == "First"
    assert get_revision(database, "2", read_mode=mode).version == 2


@pytest.mark.parametrize("mode", ["verify", "normalized"])
def test_missing_or_wrong_publication_cannot_fall_back(database, mode):
    from app.configuration.store import Publication
    publication = database.scalar(select(Publication).where(Publication.revision == 1))
    publication.source_config_id = "different"
    with pytest.raises(ConfigurationIntegrityError, match="linked"):
        get_revision(database, "1", read_mode=mode)
    assert get_revision(database, "missing", read_mode=mode) is None


@pytest.mark.parametrize("mode", ["verify", "normalized"])
def test_legacy_or_normalized_corruption_is_rejected(database, mode):
    record = database.get(Config, "1")
    original = copy.deepcopy(record.payload)
    record.payload = {"profiles": {}}
    with pytest.raises(ConfigurationIntegrityError, match="differ"):
        get_revision(database, "1", read_mode=mode)
    record.payload = original
    # Select by key instead of database-specific JSON equality.
    entry = database.scalars(select(ConfigurationEntry).where(ConfigurationEntry.entry_key == "synthetic")).first()
    entry.value = {"label": "Tampered"}
    with pytest.raises(ConfigurationIntegrityError, match="integrity"):
        get_revision(database, "1", read_mode=mode)


def test_unknown_read_mode_is_rejected(database):
    with pytest.raises(ValueError, match="read mode"):
        resolve_revision(database, database.get(Config, "1"), read_mode="typo")
