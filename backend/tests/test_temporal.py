"""Actual Temporal test-service integration; runs a real workflow and threaded activity."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from concurrent.futures import ThreadPoolExecutor

from app.db import CaseRun, Job, SessionLocal
from app.worker import (
    process_case_sop,
    process_document,
    record_case_failure,
    record_workflow_failure,
)
from app.workflow import CaseSOPWorkflow, DocumentWorkflow
from sqlalchemy import select
from temporalio import activity
from temporalio.exceptions import ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
from test_platform import publish_fixture, upload


def test_worker_connects_to_selected_namespace(monkeypatch):
    from app import worker
    connect = AsyncMock(return_value=object())
    monkeypatch.setattr(worker.Client, 'connect', connect)
    monkeypatch.setattr(worker, 'settings', SimpleNamespace(
        temporal='temporal:7233', temporal_namespace='isolated-test',
        concurrency=1, task_queue='isolated-queue'))
    monkeypatch.setattr(worker, 'Worker', lambda *a, **k: SimpleNamespace(
        run=AsyncMock(side_effect=RuntimeError('registration verified'))))
    monkeypatch.setattr(worker, 'dispatch', AsyncMock(return_value=None))
    with pytest.raises(RuntimeError, match='registration verified'):
        asyncio.run(worker.temporal_main())
    connect.assert_awaited_once_with('temporal:7233', namespace='isolated-test')


def test_temporal_document_workflow(signed):
    publish_fixture(signed)
    case_id = upload(signed, names=("rina_ektp.pdf",), template="custom").json()[
        "case_ids"
    ][0]
    with SessionLocal() as db:
        job_id = db.scalar(select(Job.id))

    async def run():
        async with await WorkflowEnvironment.start_time_skipping() as env:
            with ThreadPoolExecutor(max_workers=2) as executor:
                async with Worker(
                    env.client,
                    task_queue="sqe-test",
                    workflows=[DocumentWorkflow, CaseSOPWorkflow],
                    activities=[
                        process_document,
                        record_workflow_failure,
                        process_case_sop,
                        record_case_failure,
                    ],
                    activity_executor=executor,
                ):
                    await env.client.execute_workflow(
                        DocumentWorkflow.run,
                        job_id,
                        id="test-" + job_id,
                        task_queue="sqe-test",
                    )
                    with SessionLocal() as db:
                        run_id = db.scalar(select(CaseRun.id))
                    await env.client.execute_workflow(
                        CaseSOPWorkflow.run,
                        run_id,
                        id="sop-test-" + run_id,
                        task_queue="sqe-test",
                    )

    asyncio.run(run())
    detail = signed.get("/api/cases/" + case_id).json()
    assert detail["documents"][0]["status"] == "COMPLETED"
    assert detail["reports"]


@activity.defn(name="process_document")
def fail_activity(job_id: str):
    raise ApplicationError("Synthetic worker crash", non_retryable=True)


def test_failed_temporal_activity_becomes_visible_case_error(signed):
    publish_fixture(signed)
    case_id = upload(signed, names=("crash_ektp.pdf",), template="custom").json()[
        "case_ids"
    ][0]
    with SessionLocal() as db:
        job_id = db.scalar(select(Job.id))

    async def run():
        async with await WorkflowEnvironment.start_time_skipping() as env:
            with ThreadPoolExecutor(max_workers=2) as executor:
                async with Worker(
                    env.client,
                    task_queue="sqe-failure-test",
                    workflows=[DocumentWorkflow, CaseSOPWorkflow],
                    activities=[
                        fail_activity,
                        record_workflow_failure,
                        process_case_sop,
                        record_case_failure,
                    ],
                    activity_executor=executor,
                ):
                    await env.client.execute_workflow(
                        DocumentWorkflow.run,
                        job_id,
                        id="failure-" + job_id,
                        task_queue="sqe-failure-test",
                    )
                    with SessionLocal() as db:
                        run_id = db.scalar(select(CaseRun.id))
                    await env.client.execute_workflow(
                        CaseSOPWorkflow.run,
                        run_id,
                        id="sop-failure-" + run_id,
                        task_queue="sqe-failure-test",
                    )

    asyncio.run(run())
    detail = signed.get("/api/cases/" + case_id).json()
    assert detail["status"] == "PROCESSING_ERROR"
    assert detail["documents"][0]["status"] == "ERROR"
    assert signed.get("/api/inbox").json()
