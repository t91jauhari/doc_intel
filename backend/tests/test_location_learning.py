import copy
from types import SimpleNamespace
import fitz
from sqlalchemy import select
from app.db import Document, LocationFeedback, SessionLocal
from app.domain import default_config
from app.location_learning import retrieve, compatible, prompt
from app.storage import original_key
from test_platform import publish_fixture, process_all


def form(width=600, height=800, first_entry="observed entry"):
    pdf = fitz.open()
    page = pdf.new_page(width=width, height=height)
    for i in range(28):
        page.insert_text(
            (45, 45 + i * 22),
            f"Form field label {i}: {first_entry if i == 0 else 'observed entry'}",
            fontsize=10,
        )
        page.draw_rect(fitz.Rect(350, 35 + i * 22, 540, 51 + i * 22))
    data = pdf.tobytes()
    pdf.close()
    return data


def upload_form(signed, name, key):
    branch = signed.get("/api/branches").json()[0]["id"]
    result = signed.post(
        "/api/uploads",
        data={"branch_id": branch, "template": "custom"},
        files=[("files", (name, form(first_entry=name), "application/pdf"))],
        headers={"Idempotency-Key": key},
    )
    assert result.status_code == 202, result.text
    process_all()
    return signed.get("/api/cases/" + result.json()["case_ids"][0]).json()["documents"][
        0
    ]


def test_corrections_persist_reuse_scoping_versions_and_retirement(signed):
    publish_fixture(signed)
    first = upload_form(signed, "First_transaction.pdf", "first")
    body = {
        "field": "branch",
        "page_number": 1,
        "bbox": [0.05, 0.04, 0.6, 0.08],
        "reason": "Reviewed branch-labelled region",
        "learn_for_future": True,
    }
    result = signed.post("/api/documents/" + first["id"] + "/visual-box", json=body)
    assert result.status_code == 202, result.text
    sample_id = result.json()["location_feedback_id"]
    second = upload_form(signed, "Second_transaction.pdf", "second")
    with SessionLocal() as db:
        target = db.get(Document, second["id"])
        profile = default_config()["profiles"]["application"]
        hints = retrieve(db, target, profile)
        assert len(hints) == 1 and hints[0]["sample_ids"] == [sample_id]
        assert hints[0]["bbox"] == body["bbox"]
        assert "REMITTANCE" not in prompt(
            hints
        ) and "current-document observations only" in prompt(hints)
        other = SimpleNamespace(
            id="other",
            org="other",
            branch_id=target.branch_id,
            doc_type=target.doc_type,
            provider_state={"storage_key": original_key(target)},
        )
        assert retrieve(db, other, profile) == []
        other.org = target.org
        other.branch_id = "other-branch"
        assert retrieve(db, other, profile) == []
        changed = copy.deepcopy(profile)
        changed["schema"]["properties"]["new_field"] = {"type": ["string", "null"]}
        assert retrieve(db, target, changed) == []
    # Revision replaces only future reuse; both records remain in history.
    body["bbox"] = [0.1, 0.1, 0.4, 0.15]
    revised = signed.post("/api/documents/" + first["id"] + "/visual-box", json=body)
    assert revised.status_code == 202
    history = signed.get("/api/location-learning?document_type=application").json()
    assert (
        len(history) == 2
        and next(s for s in history if s["id"] == sample_id)["enabled"] is False
    )
    assert (
        signed.post(
            "/api/location-learning/"
            + revised.json()["location_feedback_id"]
            + "/disable"
        ).status_code
        == 200
    )
    with SessionLocal() as db:
        assert retrieve(db, db.get(Document, second["id"]), profile) == []


def test_blank_field_regions_can_be_added_without_inventing_a_value(signed):
    publish_fixture(signed)
    document = upload_form(signed, "Blank_transaction.pdf", "blank")
    with SessionLocal.begin() as db:
        doc = db.get(Document, document["id"])
        doc.raw = {**doc.raw, "notes": None}
    result = signed.post(
        "/api/documents/" + document["id"] + "/visual-box",
        json={
            "field": "notes",
            "page_number": 1,
            "bbox": [0.1, 0.1, 0.4, 0.2],
            "reason": "Inspected blank notes region",
            "learn_for_future": False,
        },
    )
    assert result.status_code == 202, result.text
    with SessionLocal() as db:
        doc = db.get(Document, document["id"])
        assert doc.raw["notes"] is None
        item = next(
            e for e in doc.validation["field_evidence"] if e["field"] == "notes"
        )
        assert item["available"] and item["review_status"] == "REVIEWED"
        assert (
            db.scalar(
                select(LocationFeedback).where(LocationFeedback.document_id == doc.id)
            ).enabled
            is False
        )


def test_layout_mismatch_and_featureless_forms_never_match():
    left = {"version": 1, "pages": [{"aspect": 0.75, "hash": "ff" * 32}]}
    assert not compatible(
        left, {"version": 1, "pages": [{"aspect": 1.2, "hash": "ff" * 32}]}
    )
    assert not compatible(
        left, {"version": 1, "pages": [{"aspect": 0.75, "hash": "00" * 32}]}
    )
    assert not compatible(left, {"version": 1, "pages": []})
    assert not compatible(left, {})
