"""Transactional publication service with an explicit dual-storage rollout mode."""
import hashlib
import json

from sqlalchemy import inspect, text

from .migrate import MIGRATIONS
from .service import StaleConfiguration
from .store import ConfigurationBase, import_publication, compile_publication, fingerprint


class ConfigurationStorageNotReady(RuntimeError):
    pass


def require_storage_schema(session):
    connection = session.connection()
    inspector = inspect(connection)
    required = set(ConfigurationBase.metadata.tables)
    if connection.dialect.name == "postgresql":
        required.add("configuration_schema_migrations")
    if any(not inspector.has_table(table) for table in required):
        raise ConfigurationStorageNotReady("Configuration storage is not ready. Apply explicit schema migrations before enabling dual mode.")
    if connection.dialect.name == "postgresql":
        applied = dict(connection.execute(text("SELECT version,checksum FROM configuration_schema_migrations")).all())
        expected = {path.stem: hashlib.sha256(path.read_text(encoding="utf-8").encode()).hexdigest()
                    for path in MIGRATIONS.glob("[0-9][0-9][0-9][0-9]_*.sql")}
        if applied != expected:
            raise ConfigurationStorageNotReady("Configuration migration history does not match this release.")


def publish_configuration(session, *, organization, actor, expected_version, payload, storage_mode):
    """Caller owns commit/rollback; source payload and historical pins stay intact."""
    from app.db import Config
    from app.domain import validate_config, audit
    from app.profile_guidance import locked_latest_config
    from app.extraction_prompts import system_instruction

    if storage_mode not in {"legacy", "dual"}:
        raise ValueError("Unknown configuration storage mode.")
    # Match the existing JSON persistence contract without mutating request data.
    draft = json.loads(json.dumps(payload, ensure_ascii=False, allow_nan=False))
    if not isinstance(draft, dict) or not isinstance(draft.get("profiles", {}), dict) or any(
        not isinstance(profile, dict) for profile in draft.get("profiles", {}).values()
    ):
        raise ValueError("Configuration profiles must be objects.")
    for profile in draft.get("profiles", {}).values():
        profile["system_instruction"] = system_instruction(profile)
    validate_config(draft)
    previous = locked_latest_config(session, organization)
    if previous.version != expected_version:
        raise StaleConfiguration("Configuration changed. Reload before publishing.")
    if storage_mode == "dual":
        require_storage_schema(session)
    saved = Config(org=organization, version=previous.version + 1, payload=draft, published_by=actor)
    session.add(saved)
    session.flush()
    publication = None
    if storage_mode == "dual":
        publication = import_publication(session, organization=organization, revision=saved.version,
                                         source_config_id=saved.id, payload=draft)
        if fingerprint(compile_publication(session, publication)) != fingerprint(draft):
            raise ValueError("Published configuration reconstruction differs from its source.")
    audit(session, organization, actor, "config.published", version=saved.version,
          previous_version=previous.version, storage_mode=storage_mode,
          publication_id=publication.id if publication else None)
    result = {"id": saved.id, "version": saved.version, "payload": draft}
    if publication:
        result["publication_id"] = publication.id
    return result
