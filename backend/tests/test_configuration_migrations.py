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


def test_failed_ddl_rolls_back_entire_migration(isolated_engine, tmp_path, monkeypatch):
    (tmp_path / "0001_bad.sql").write_text(
        "CREATE TABLE partial_table(id INTEGER); INVALID SQL;", encoding="utf-8"
    )
    monkeypatch.setattr(migrate, "MIGRATIONS", tmp_path)
    with pytest.raises(ProgrammingError):
        migrate.apply_migrations(isolated_engine, expected_database="sqe_refactor")
    with isolated_engine.connect() as connection:
        assert connection.scalar(text("SELECT to_regclass('partial_table')")) is None
        assert connection.scalar(text("SELECT to_regclass('configuration_schema_migrations')")) is None


def test_replay_and_checksum_protection(isolated_engine, tmp_path, monkeypatch):
    path = tmp_path / "0001_test.sql"
    path.write_text("CREATE TABLE sample(id INTEGER);", encoding="utf-8")
    monkeypatch.setattr(migrate, "MIGRATIONS", tmp_path)
    assert migrate.apply_migrations(isolated_engine, expected_database="sqe_refactor") == ["0001_test"]
    assert migrate.apply_migrations(isolated_engine, expected_database="sqe_refactor") == []
    path.write_text("CREATE TABLE changed(id INTEGER);", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum"):
        migrate.apply_migrations(isolated_engine, expected_database="sqe_refactor")


def test_identity_bindings_round_trip_in_postgres(isolated_engine):
    from sqlalchemy.orm import Session
    from app.configuration.store import compile_publication, import_publication

    assert migrate.apply_migrations(isolated_engine, expected_database="sqe_refactor") == [
        "0001_publications", "0002_identity_bindings",
    ]
    payload = {
        "profiles": {"custom": {"schema": {"type": "object", "properties": {
            "name": {"type": "string"},
        }}}},
        "identity_policy": {"bindings": [{"profile": "custom", "field_path": "name"}]},
    }
    with Session(isolated_engine) as session, session.begin():
        publication = import_publication(session, organization="test", revision=1,
                                         source_config_id="synthetic", payload=payload)
        assert compile_publication(session, publication) == payload
        assert session.scalar(text("SELECT count(*) FROM configuration_identity_bindings")) == 1
