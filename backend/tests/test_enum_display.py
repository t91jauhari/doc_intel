import copy
from types import SimpleNamespace
import pytest
from sqlalchemy import select
from app.db import Case, Config, Document, Job, SessionLocal
from app.domain import default_config, latest_config
from app.enum_aliases import seed_enum_aliases, validate_aliases
from app.provider import validate_extraction
from app.value_display import display_value
from test_platform import upload


def test_display_does_not_mutate_structured_evidence():
    value = {
        "present": True,
        "text": "COPY SESUAI ASLINYA",
        "complete": True,
        "evidence": "Source observation",
    }
    original = copy.deepcopy(value)
    assert display_value(value) == "Present · Complete · COPY SESUAI ASLINYA"
    assert value == original
    assert (
        display_value({"place": "KOTA YOGYAKARTA", "date": "13-06-2017"})
        == "KOTA YOGYAKARTA — 13 Juni 2017"
    )
    assert display_value("-") == "-"
    assert display_value(None) == "Missing"
    assert display_value({"present": None}) == "Needs review"
    assert display_value({"present": False}) == "Absent"


def test_result_only_display_preserves_checkbox_and_party_data():
    selection = {
        "selected": "REMITTANCE",
        "options_complete": True,
        "options": [
            {"label": "RTGS", "state": "unselected", "local_mark_present": False},
            {"label": "REMITTANCE", "state": "selected", "local_mark_present": True},
        ],
    }
    original = copy.deepcopy(selection)
    assert display_value(selection) == "REMITTANCE"
    assert selection == original
    assert display_value({**selection, "selected": None}) == "Missing"
    assert display_value({**selection, "selected": []}) == "None selected"
    party = {
        "full_text": "ORANGE SOFTWARE (HK) Ltd.\n9300 Flair drive",
        "name": "ORANGE SOFTWARE (HK) Ltd.",
        "address": "9300 Flair drive",
        "phone": None,
    }
    assert display_value(party) == "ORANGE SOFTWARE (HK) Ltd. · 9300 Flair drive"
    assert (
        display_value({"name": "Observed bank", "branch": "Observed branch"})
        == "Observed bank · Observed branch"
    )
    assert (
        display_value(
            {"currency_raw": "USD", "amount_raw": "206.550", "segmented_cells": True}
        )
        == "USD 206.550"
    )


def test_alias_policy_rejects_unknown_targets_and_remapping():
    policy = default_config()["profiles"]["ektp"]["policy"]
    validate_aliases(policy)
    for alias in [
        {"KATHOLIK": "Unknown"},
        {"Islam": "Katolik"},
        {"A": "Katolik", "a": "Katolik"},
    ]:
        bad = copy.deepcopy(policy)
        bad["enum_aliases"] = {"religion": alias}
        with pytest.raises(ValueError):
            validate_aliases(bad)


def test_approved_alias_uses_saved_raw_and_records_transformation():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "engine/tests"))
    from test_ektp import evidence, metadata, comparison_context

    cfg = default_config()
    cfg['provider'] = 'llama'  # This test exercises the native enum validator.
    raw = evidence()
    raw["religion"] = "KATHOLIK"
    doc = SimpleNamespace(doc_type="ektp", overrides={}, provider_state={})
    result = validate_extraction(
        doc,
        cfg,
        {
            "extract_result": raw,
            "extract_metadata": metadata(),
            "id": "ext-synthetic-ektp",
        },
    )
    assert result["normalized"]["religion"] == "Katolik"
    assert result["original_raw"]["religion"] == "KATHOLIK"
    assert any(
        c["field"] == "religion" and c["method"] == "approved_enum_alias"
        for c in result["corrections"]
    )
    raw["religion"] = "Katolikk"
    result = validate_extraction(
        doc, cfg, {"extract_result": raw, "extract_metadata": metadata()}
    )
    assert result["fields"]["religion"]["status"] == "REVIEW"
    assert result["normalized"]["religion"] == "Katolikk"


def test_alias_seed_idempotence_and_case_revalidation_no_prompt_change(
    signed, monkeypatch
):
    case_id = upload(signed, names=("Customer_ektp.pdf",), key="alias-case").json()[
        "case_ids"
    ][0]
    with SessionLocal.begin() as db:
        case = db.get(Case, case_id)
        config_id = case.config_id
        document = db.scalar(select(Document).where(Document.case_id == case_id))
        document.status = "COMPLETED"
        from test_ektp import evidence, metadata

        document.raw = evidence()
        document.raw["religion"] = "KATHOLIK"
        document.metadata_json = metadata()
        for job in db.scalars(select(Job).where(Job.document_id == document.id)):
            job.status = "COMPLETED"
        version = latest_config(db, "sqe").version
    seed_enum_aliases()
    seed_enum_aliases()
    response = signed.post(
        f"/api/cases/{case_id}/revalidate-enum-aliases",
        json={"reason": "Apply approved spelling policy"},
    )
    assert response.status_code == 202, response.text
    with SessionLocal() as db:
        assert latest_config(db, "sqe").version == version
        assert db.get(Case, case_id).config_id == config_id
        d = db.scalar(select(Document).where(Document.case_id == case_id))
        assert d.raw["religion"] == "KATHOLIK"
        assert (
            d.provider_state["normalization_enum_aliases"]["religion"]["KATHOLIK"]
            == "Katolik"
        )
        job = db.scalar(
            select(Job).where(Job.document_id == d.id, Job.status == "QUEUED")
        )
        assert job.action == "revalidate"
        job_id = job.id
    assert (
        signed.post(
            f"/api/cases/{case_id}/revalidate-enum-aliases",
            json={"reason": "Second attempt blocked"},
        ).status_code
        == 409
    )

    import app.processor as processor

    monkeypatch.setattr(
        processor,
        "run_provider",
        lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("No paid extraction expected")
        ),
    )
    processor.process_job(job_id)
    with SessionLocal() as db:
        d = db.scalar(select(Document).where(Document.case_id == case_id))
        assert d.normalized["religion"] == "Katolik"
        assert d.raw["religion"] == "KATHOLIK"


@pytest.mark.parametrize(
    "value, expected",
    [
        ("islam", "Islam"),
        ("budha", "Buddha"),
        ("katholik", "Katolik"),
        ("HINDU", "Hindu"),
        ("Other printed belief", "Other printed belief"),
        ("  Local belief  ", "Local belief"),
        (None, None),
        ("", None),
    ],
)
def test_religion_canonical_or_raw_fallback(value, expected):
    from test_ektp import evidence, metadata

    cfg = default_config()
    cfg['provider'] = 'llama'  # Spider preserves model values unless explicitly revalidated.
    raw = evidence()
    raw["religion"] = value
    doc = SimpleNamespace(doc_type="ektp", overrides={}, provider_state={})
    result = validate_extraction(
        doc, cfg, {"extract_result": raw, "extract_metadata": metadata()}
    )
    assert result["normalized"]["religion"] == expected
    assert result["original_raw"]["religion"] == value
    if expected in {"Other printed belief", "Local belief"}:
        assert result["fields"]["religion"]["status"] == "REVIEW"
        assert any(
            c["method"] == "unrecognized_enum_raw_fallback" and c["review_required"]
            for c in result["corrections"]
        )
    cfg["profiles"]["ektp"]["policy"]["enum_raw_fallback_fields"] = []
    if expected in {"Other printed belief", "Local belief"}:
        assert (
            validate_extraction(
                doc, cfg, {"extract_result": raw, "extract_metadata": metadata()}
            )["normalized"]["religion"]
            is None
        )
