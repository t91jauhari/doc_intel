from copy import deepcopy
from types import SimpleNamespace

from app.db import Config, SessionLocal
from app.domain import default_config, riplay_identity_findings, route, upgrade_profiles
from sqlalchemy import select
from test_platform import PDF, process_all, publish_fixture


def test_riplay_registered_and_classification_routes_by_suffix():
    cfg = default_config()
    profile = cfg["profiles"]["riplay"]
    assert len(profile["columns"]) == 10
    assert "four pages" in profile["classification_description"]
    actual_type, customer, _ = route("Indah Laruna_riplay.pdf", cfg)
    assert actual_type == "riplay" and customer == "Indah Laruna"


def test_riplay_fixture_worker_and_separate_csv(signed):
    publish_fixture(signed)
    branch = signed.get("/api/branches").json()[0]["id"]
    result = signed.post(
        "/api/uploads",
        data={"branch_id": branch, "template": "custom"},
        files=[
            ("files", ("rina_riplay.pdf", PDF, "application/pdf")),
            (
                "files",
                ("rina_ektp.pdf", PDF + b"\n% different card", "application/pdf"),
            ),
        ],
        headers={"Idempotency-Key": "riplay-and-ektp"},
    )
    assert result.status_code == 202
    case_id = result.json()["case_ids"][0]
    process_all()
    detail = signed.get("/api/cases/" + case_id).json()
    assert len(detail["documents"]) == 2
    assert all(doc["status"] == "COMPLETED" for doc in detail["documents"])
    findings = [
        f
        for f in detail["reports"][0]["snapshot"]["findings"]
        if f["rule_id"] == "SYS_03_RIPLAY_NAME"
    ]
    assert len(findings) == 1 and findings[0]["result"] == "PASS"
    csv = signed.get("/api/exports/riplay")
    assert csv.status_code == 200
    assert "document_place" in csv.text and "page_initials" in csv.text
    assert "rina_riplay.pdf" in csv.text and "rina_ektp.pdf" not in csv.text
    assert detail["reports"]


def test_identity_missing_mismatched_ambiguous_and_unreadable():
    cfg = default_config()
    riplay = SimpleNamespace(
        doc_type="riplay",
        status="COMPLETED",
        normalized={"customer_name": "Rina Putri"},
        id="riplay",
        validation={},
    )
    ektp = SimpleNamespace(
        doc_type="ektp",
        status="COMPLETED",
        normalized={"name": "rina  putri"},
        id="ektp",
        validation={"fields": {"name": {"status": "PASS"}}},
    )
    assert riplay_identity_findings([riplay], cfg)[0]["result"] == "REVIEW"
    assert riplay_identity_findings([riplay, ektp], cfg)[0]["result"] == "PASS"
    ektp.normalized["name"] = "Other Customer"
    assert riplay_identity_findings([riplay, ektp], cfg)[0]["result"] == "FAIL"
    assert (
        riplay_identity_findings([riplay, ektp, deepcopy(ektp)], cfg)[0]["result"]
        == "REVIEW"
    )
    ektp.validation["fields"]["name"]["status"] = "REVIEW"
    assert riplay_identity_findings([riplay, ektp], cfg)[0]["result"] == "REVIEW"
    assert riplay_identity_findings([ektp], cfg) == []


def test_profile_upgrade_preserves_pinned_configuration_and_customizations(signed):
    with SessionLocal.begin() as db:
        old = db.scalar(select(Config).where(Config.org == "sqe").order_by(Config.version.desc()).limit(1))
        payload = deepcopy(old.payload)
        payload["profiles"].pop("riplay")
        payload["report_title"] = "Custom bank title"
        old.payload = payload
        old_id, old_version = old.id, old.version
        assert upgrade_profiles(db, "sqe")
    with SessionLocal() as db:
        previous = db.get(Config, old_id)
        current = db.scalar(select(Config).order_by(Config.version.desc()))
        assert "riplay" not in previous.payload["profiles"]
        assert current.version == old_version + 1
        assert current.payload["report_title"] == "Custom bank title"
        assert "riplay" in current.payload["profiles"]
        assert not upgrade_profiles(db, "sqe")
