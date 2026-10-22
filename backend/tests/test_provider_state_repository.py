from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import os
import threading
import time

import pytest
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import sessionmaker

from app.db import Document
from app.extraction.contracts import ProcessingIssue
from app.extraction.state_repository import SqlProviderState


def document():
    return Document(id="synthetic", org="synthetic", branch_id="branch", case_id="case", batch_id="batch",
                    filename="synthetic.pdf", sha256="0" * 64, provider_state={"existing": {"value": 1}})


@pytest.fixture
def sessions():
    engine = create_engine("sqlite://")
    Document.__table__.create(engine)
    factory = sessionmaker(engine)
    with factory.begin() as session:
        session.add(document())
    yield factory
    engine.dispose()


def test_checkpoint_is_durable_and_copies_nested_state(sessions):
    state = SqlProviderState(sessions)
    update = {"request": {"id": "request"}}
    with pytest.raises(RuntimeError):
        with sessions.begin():
            state.checkpoint("synthetic", "EXTRACTING", **update)
            raise RuntimeError("Later processing rolled back")
    update["request"]["id"] = "changed"
    result = state.read("synthetic")
    assert result == {"existing": {"value": 1}, "request": {"id": "request"}}
    result["existing"]["value"] = 99
    assert state.read("synthetic")["existing"]["value"] == 1
    with sessions() as session:
        assert session.get(Document, "synthetic").status == "EXTRACTING"


def test_invalid_checkpoint_rolls_back_without_losing_prior_state(sessions):
    state = SqlProviderState(sessions)
    with pytest.raises(StatementError):
        state.checkpoint("synthetic", "EXTRACTING", invalid=object())
    assert state.read("synthetic") == {"existing": {"value": 1}}
    with sessions() as session:
        assert session.get(Document, "synthetic").status == "QUEUED"


def test_missing_document_fails_before_submission(sessions):
    state = SqlProviderState(sessions)
    with pytest.raises(ProcessingIssue, match="cannot be read"):
        state.read("missing")
    with pytest.raises(ProcessingIssue, match="not started"):
        state.checkpoint("missing", pending_create="extract")


def test_postgres_concurrent_checkpoint_merges_committed_receipt():
    url = os.environ.get("REFACTOR_MIGRATION_TEST_URL")
    if not url:
        pytest.skip("Explicit isolated PostgreSQL URL required.")
    engine = create_engine(url)
    with engine.begin() as connection:
        assert connection.scalar(text("SELECT current_database()")) == "sqe_refactor"
        connection.execute(text("CREATE SCHEMA provider_state_contract_tests"))

    @event.listens_for(engine, "checkout")
    def scope(connection, *_):
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO provider_state_contract_tests")
        connection.commit()

    held, executor = None, None
    try:
        Document.__table__.create(engine)
        sessions = sessionmaker(engine)
        with sessions.begin() as session:
            session.add(document())
        held = sessions()
        first = held.scalar(select(Document).where(Document.id == "synthetic").with_for_update())
        ready = threading.Event()
        process_id = []
        class TrackedSessions:
            @contextmanager
            def begin(self):
                with sessions.begin() as session:
                    process_id.append(session.scalar(text("SELECT pg_backend_pid()")))
                    ready.set()
                    yield session
        executor = ThreadPoolExecutor(max_workers=1)
        pending = executor.submit(SqlProviderState(TrackedSessions()).checkpoint, "synthetic", second_receipt="second")
        assert ready.wait(10)
        blocked = False
        deadline = time.monotonic() + 10
        with engine.connect() as observer:
            while time.monotonic() < deadline:
                if observer.scalar(text("SELECT cardinality(pg_blocking_pids(:pid))"), {"pid": process_id[0]}):
                    blocked = True
                    break
                ready.wait(0.01)
        assert blocked, "Expected a concurrent state write to wait for the held document row."
        first.provider_state = {**first.provider_state, "first_receipt": "first"}
        held.commit()
        pending.result(timeout=10)
        assert SqlProviderState(sessions).read("synthetic") == {
            "existing": {"value": 1}, "first_receipt": "first", "second_receipt": "second"}
    finally:
        if held:
            held.rollback()
            held.close()
        if executor:
            executor.shutdown(wait=True, cancel_futures=True)
        event.remove(engine, "checkout", scope)
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA provider_state_contract_tests CASCADE"))
        engine.dispose()
