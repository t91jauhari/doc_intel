"""Lossless compatibility storage for immutable configuration publications.

Independent metadata deliberately prevents application startup from creating or
activating these tables. The caller owns migrations and transaction boundaries.
"""
import copy
import hashlib
import json
import uuid

from sqlalchemy import JSON, ForeignKey, Integer, String, UniqueConstraint, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class ConfigurationBase(DeclarativeBase):
    pass


class Publication(ConfigurationBase):
    __tablename__ = "configuration_publications"
    __table_args__ = (UniqueConstraint("organization", "revision"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization: Mapped[str] = mapped_column(String(80), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    source_config_id: Mapped[str] = mapped_column(String(36))
    digest: Mapped[str] = mapped_column(String(64))
    # Unmodeled extensions remain lossless while consumers migrate gradually.
    extensions: Mapped[dict] = mapped_column(JSON)


class ConfigurationEntry(ConfigurationBase):
    __tablename__ = "configuration_entries"
    __table_args__ = (UniqueConstraint("publication_id", "section", "entry_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    publication_id: Mapped[str] = mapped_column(
        ForeignKey("configuration_publications.id"), index=True
    )
    section: Mapped[str] = mapped_column(String(80))
    entry_key: Mapped[str] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer)
    value: Mapped[dict] = mapped_column(JSON)


class IdentityPolicyRecord(ConfigurationBase):
    __tablename__ = "configuration_identity_policies"
    publication_id: Mapped[str] = mapped_column(ForeignKey("configuration_publications.id"), primary_key=True)
    settings: Mapped[dict] = mapped_column(JSON)


class IdentityBindingRecord(ConfigurationBase):
    __tablename__ = "configuration_identity_bindings"
    publication_id: Mapped[str] = mapped_column(ForeignKey("configuration_identity_policies.publication_id"), primary_key=True)
    profile: Mapped[str] = mapped_column(String(80), primary_key=True)
    position: Mapped[int] = mapped_column(Integer)
    definition: Mapped[dict] = mapped_column(JSON)


# Structural sections only: no family names, field paths or business rules.
MAPPING_SECTIONS = ("document_families", "profiles", "profile_variants", "templates")
LIST_SECTIONS = ("sop_rules",)


def fingerprint(payload: dict) -> str:
    return hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode()).hexdigest()


def import_publication(
    session: Session, *, organization: str, revision: int,
    source_config_id: str, payload: dict,
) -> Publication:
    """Import once, reject revision rewrites, never commit or activate."""
    if not organization.strip() or revision < 1 or not isinstance(payload, dict):
        raise ValueError("Organization, positive revision and object payload required.")
    digest = fingerprint(payload)
    existing = session.scalar(select(Publication).where(
        Publication.organization == organization, Publication.revision == revision,
    ))
    if existing:
        if existing.digest != digest or existing.source_config_id != source_config_id:
            raise ValueError("An imported revision cannot be replaced.")
        compile_publication(session, existing)
        return existing
    extensions = copy.deepcopy(payload)
    identity = extensions.pop("identity_policy", None)
    if "identity_policy" in payload:
        from .identity import IdentityPolicy, validate_bindings

        validate_bindings(IdentityPolicy.model_validate(identity), payload.get("profiles", {}))
    entries = []
    for section in MAPPING_SECTIONS + LIST_SECTIONS:
        if section not in extensions:
            continue
        values = extensions[section]
        if section in MAPPING_SECTIONS:
            if not isinstance(values, dict):
                raise ValueError(f"{section} must be an object.")
            rows = list(values.items())
        else:
            if not isinstance(values, list):
                raise ValueError(f"{section} must be a list.")
            rows = [(str(index), value) for index, value in enumerate(values)]
        for position, (key, value) in enumerate(rows):
            if not isinstance(value, dict):
                raise ValueError(f"{section}.{key} must be an object.")
            entries.append((section, key, position, value))
        # Retain empty containers to distinguish absent sections from empty ones.
        extensions[section] = {} if section in MAPPING_SECTIONS else []
    publication = Publication(
        id=str(uuid.uuid4()), organization=organization, revision=revision,
        source_config_id=source_config_id, digest=digest, extensions=extensions,
    )
    session.add(publication)
    session.flush()
    if identity is not None:
        settings = {key: copy.deepcopy(value) for key, value in identity.items() if key != "bindings"}
        session.add(IdentityPolicyRecord(publication_id=publication.id, settings=settings))
        session.flush()
        for position, binding in enumerate(identity["bindings"]):
            session.add(IdentityBindingRecord(
                publication_id=publication.id, profile=binding["profile"],
                position=position, definition=copy.deepcopy(binding),
            ))
    for section, key, position, value in entries:
        session.add(ConfigurationEntry(
            id=str(uuid.uuid4()), publication_id=publication.id, section=section,
            entry_key=key, position=position, value=value,
        ))
    session.flush()
    compile_publication(session, publication)
    return publication


def compile_publication(session: Session, publication: Publication) -> dict:
    """Reconstruct the legacy contract and detect accidental persisted changes."""
    payload = copy.deepcopy(publication.extensions)
    identity = session.get(IdentityPolicyRecord, publication.id)
    if identity is not None:
        settings = copy.deepcopy(identity.settings)
        settings["bindings"] = [copy.deepcopy(binding.definition) for binding in session.scalars(
            select(IdentityBindingRecord).where(IdentityBindingRecord.publication_id == publication.id)
            .order_by(IdentityBindingRecord.position)
        )]
        payload["identity_policy"] = settings
    entries = session.scalars(select(ConfigurationEntry).where(
        ConfigurationEntry.publication_id == publication.id,
    ).order_by(ConfigurationEntry.section, ConfigurationEntry.position)).all()
    for entry in entries:
        if entry.section in MAPPING_SECTIONS:
            payload[entry.section][entry.entry_key] = copy.deepcopy(entry.value)
        elif entry.section in LIST_SECTIONS:
            payload[entry.section].append(copy.deepcopy(entry.value))
        else:
            raise ValueError("Unknown persisted configuration section.")
    if fingerprint(payload) != publication.digest:
        raise ValueError("Configuration integrity check failed.")
    return payload
