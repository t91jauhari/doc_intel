import copy

import pytest
from sqlalchemy import func, select

from app.configuration.publication import persist_revision
from app.configuration.store import fingerprint
from app.db import Case, Config, Report, SessionLocal
from app.domain import latest_config, refresh_case


@pytest.mark.parametrize("required,status,validation", [([], "READY", "PASS"), (["ektp"], "WAITING_DOCUMENTS", "FAIL")])
def test_legacy_refresh_evaluates_without_upgrading_pinned_configuration(signed, monkeypatch, required, status, validation):
    artifacts = []
    monkeypatch.setattr("app.reporting.persist_report", lambda report: artifacts.append(report.id))
    with SessionLocal.begin() as db:
        current = latest_config(db, "sqe")
        payload = copy.deepcopy(current.payload)
        payload.pop("workflow")
        payload["rules"] = []
        payload["templates"]["forex"]["required"] = required
        record = Config(org="sqe", version=current.version + 1, payload=payload, published_by="synthetic")
        persist_revision(db, record)
        original = fingerprint(record.payload)
        case = Case(org="sqe", branch_id="synthetic", reference="legacy", customer="Synthetic",
                    template="forex", created_by="synthetic", config_id=record.id)
        db.add(case)
        db.flush()
        first = refresh_case(db, case.id)
        assert case.status == status and case.validation_status == validation
        assert first["config_id"] == record.id and first["missing"] == required
        assert fingerprint(record.payload) == original
        second = refresh_case(db, case.id)
        assert {key: value for key, value in first.items() if key != "generated_at"} == {
            key: value for key, value in second.items() if key != "generated_at"}
        assert db.scalar(select(func.count()).select_from(Report).where(Report.case_id == case.id)) == 1
        assert len(artifacts) == 1
