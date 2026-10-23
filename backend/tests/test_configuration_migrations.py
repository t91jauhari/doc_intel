"""PostgreSQL migration failure cases; enabled only with an isolated test URL."""

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

from app.configuration import migrate


@pytest.fixture
def isolated_engine():
    url = os.environ.get("REFACTOR_MIGRATION_TEST_URL")
    if not url:
        pytest.skip("Explicit isolated PostgreSQL URL not provided.")
    engine = create_engine(url)
    with engine.begin() as connection:
        assert connection.scalar(text("SELECT current_database()")) == "sqe_refactor"
        connection.execute(text("CREATE SCHEMA migration_contract_tests"))
    scoped = engine.execution_options(schema_translate_map={})
    # Dedicated schema keeps tests away from restored application tables.
    from sqlalchemy import event

    @event.listens_for(engine, "checkout")
    def search_path(dbapi_connection, *_):
        with dbapi_connection.cursor() as cursor:
            cursor.execute("SET search_path TO migration_contract_tests")
        dbapi_connection.commit()

    try:
        yield scoped
    finally:
        event.remove(engine, "checkout", search_path)
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA migration_contract_tests CASCADE"))
        engine.dispose()


def test_wrong_database_rejected(isolated_engine):
    with pytest.raises(ValueError, match="explicit target"):
        migrate.apply_migrations(isolated_engine, expected_database="wrong_database")


def test_reference_dataset_immutability_in_postgres(isolated_engine):
    from sqlalchemy.exc import DBAPIError
    from sqlalchemy.orm import Session
    from app.configuration.datasets import register_dataset, read_dataset

    migrate.apply_migrations(isolated_engine, expected_database="sqe_refactor")
    payload = {
        "id": "synthetic-v1",
        "source_name": "Synthetic",
        "sha256": "0" * 64,
        "samples": [],
        "rows": [],
    }
    with Session(isolated_engine) as session, session.begin():
        register_dataset(session, "synthetic", payload)
    for sql in [
        "UPDATE reference_datasets SET digest=digest",
        "DELETE FROM reference_datasets",
        "TRUNCATE reference_datasets",
    ]:
        with pytest.raises(DBAPIError, match="immutable"):
            with isolated_engine.begin() as connection:
                connection.execute(text(sql))
    with Session(isolated_engine) as session:
        assert read_dataset(session, "synthetic", "synthetic-v1") == payload


def test_failed_ddl_rolls_back_entire_migration(isolated_engine, tmp_path, monkeypatch):
    (tmp_path / "0001_bad.sql").write_text(
        "CREATE TABLE partial_table(id INTEGER); INVALID SQL;", encoding="utf-8"
    )
    monkeypatch.setattr(migrate, "MIGRATIONS", tmp_path)
    with pytest.raises(ProgrammingError):
        migrate.apply_migrations(isolated_engine, expected_database="sqe_refactor")
    with isolated_engine.connect() as connection:
        assert connection.scalar(text("SELECT to_regclass('partial_table')")) is None
        assert (
            connection.scalar(
                text("SELECT to_regclass('configuration_schema_migrations')")
            )
            is None
        )


def test_replay_and_checksum_protection(isolated_engine, tmp_path, monkeypatch):
    path = tmp_path / "0001_test.sql"
    path.write_text("CREATE TABLE sample(id INTEGER);", encoding="utf-8")
    monkeypatch.setattr(migrate, "MIGRATIONS", tmp_path)
    assert migrate.apply_migrations(
        isolated_engine, expected_database="sqe_refactor"
    ) == ["0001_test"]
    assert (
        migrate.apply_migrations(isolated_engine, expected_database="sqe_refactor")
        == []
    )
    path.write_text("CREATE TABLE changed(id INTEGER);", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum"):
        migrate.apply_migrations(isolated_engine, expected_database="sqe_refactor")


def test_identity_bindings_round_trip_in_postgres(isolated_engine):
    from sqlalchemy.orm import Session
    from app.configuration.store import compile_publication, import_publication

    assert migrate.apply_migrations(
        isolated_engine, expected_database="sqe_refactor"
    ) == [
        "0001_publications",
        "0002_identity_bindings",
        "0003_family_rule_membership",
        "0004_revision_immutability",
        "0005_context_definitions",
        "0006_reference_datasets",
        "0007_configuration_entities",
    ]
    payload = {
        "profiles": {
            "custom": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                }
            }
        },
        "identity_policy": {"bindings": [{"profile": "custom", "field_path": "name"}]},
        "context_definitions": {
            "review_choice": {
                "label": "Review choice",
                "kind": "enum",
                "options": ["YES", "NO"],
            }
        },
        "sop_rules": [{"id": "sample_rule"}],
        "rule_scope": {
            "family_rule_ids": {"forex": ["sample_rule"], "account_opening": []}
        },
    }
    with Session(isolated_engine) as session, session.begin():
        publication = import_publication(
            session,
            organization="test",
            revision=1,
            source_config_id="synthetic",
            payload=payload,
        )
        assert compile_publication(session, publication) == payload
        assert (
            session.scalar(text("SELECT count(*) FROM configuration_identity_bindings"))
            == 1
        )
        assert (
            session.scalar(
                text("SELECT count(*) FROM configuration_family_rule_members")
            )
            == 1
        )
        assert (
            session.scalar(
                text("SELECT count(*) FROM configuration_context_definitions")
            )
            == 1
        )


def test_publication_requires_intact_migration_history(isolated_engine):
    from sqlalchemy.orm import Session
    from app.configuration.publication import (
        require_storage_schema,
        ConfigurationStorageNotReady,
    )

    migrate.apply_migrations(isolated_engine, expected_database="sqe_refactor")
    with Session(isolated_engine) as session:
        require_storage_schema(session)
        session.execute(
            text("UPDATE configuration_schema_migrations SET checksum=:checksum"),
            {"checksum": "0" * 64},
        )
        with pytest.raises(ConfigurationStorageNotReady, match="migration history"):
            require_storage_schema(session)
        session.rollback()


def test_committed_revision_tables_reject_rewrites_and_late_entries(isolated_engine):
    from sqlalchemy.exc import DBAPIError
    from sqlalchemy.orm import Session
    from app.configuration.store import (
        ConfigurationBase,
        import_publication,
        compile_publication,
    )

    with isolated_engine.begin() as connection:
        connection.execute(text("CREATE TABLE configurations(id TEXT PRIMARY KEY)"))
        connection.execute(text("INSERT INTO configurations VALUES ('historical')"))
    migrate.apply_migrations(isolated_engine, expected_database="sqe_refactor")
    payload = {
        "profiles": {
            "custom": {
                "schema": {"type": "object", "properties": {"name": {"type": "string"}}}
            }
        },
        "identity_policy": {"bindings": [{"profile": "custom", "field_path": "name"}]},
        "sop_rules": [{"id": "synthetic"}],
        "rule_scope": {
            "family_rule_ids": {"forex": ["synthetic"], "account_opening": []}
        },
    }
    with Session(isolated_engine) as session, session.begin():
        publication = import_publication(
            session,
            organization="synthetic",
            revision=1,
            source_config_id="historical",
            payload=payload,
        )
        publication_id = publication.id
        assert compile_publication(session, publication) == payload
    tables = {
        name: next(iter(table.primary_key.columns)).name
        for name, table in ConfigurationBase.metadata.tables.items()
    }
    tables["configurations"] = "id"
    for table, column in tables.items():
        for statement in (
            f"DELETE FROM {table}",
            f"UPDATE {table} SET {column}={column}",
            f"TRUNCATE {table} CASCADE",
        ):
            with pytest.raises(DBAPIError, match="immutable"):
                with isolated_engine.begin() as connection:
                    connection.execute(text(statement))
    late_inserts = [
        "INSERT INTO configuration_entries(id,publication_id,section,entry_key,position,value) VALUES ('late',:publication,'profiles','late',99,'{}')",
        "INSERT INTO configuration_identity_policies(publication_id,settings) VALUES (:publication,'{}')",
        "INSERT INTO configuration_identity_bindings(publication_id,profile,position,definition) VALUES (:publication,'late',99,'{}')",
        "INSERT INTO configuration_family_rule_scopes(publication_id,family) VALUES (:publication,'late')",
        "INSERT INTO configuration_family_rule_members(publication_id,family,rule_id,position) VALUES (:publication,'forex','late',99)",
        "INSERT INTO configuration_context_definitions(publication_id,context_key,position,definition) VALUES (:publication,'late',99,'{}')",
    ]
    for statement in late_inserts:
        with pytest.raises(DBAPIError, match="transaction creating"):
            with isolated_engine.begin() as connection:
                connection.execute(text(statement), {"publication": publication_id})
    # New revisions and idempotent imports remain valid after immutability.
    with Session(isolated_engine) as session, session.begin():
        existing = import_publication(
            session,
            organization="synthetic",
            revision=1,
            source_config_id="historical",
            payload=payload,
        )
        assert existing.id == publication_id
        new = import_publication(
            session,
            organization="synthetic",
            revision=2,
            source_config_id="new-revision",
            payload=payload,
        )
        assert compile_publication(session, new) == payload
