import base64
from concurrent.futures import ThreadPoolExecutor
import uuid
import fitz
import httpx
import pytest
from sqlalchemy import select
from app.db import Case, Config, Document, SpiderConnector, SessionLocal
from app.domain import default_config
from app.provider import run_provider, fixture_response, ProcessingIssue
from app.spider_provider import content_json, MODEL
from app.worker_capacity import initialize_slots, try_acquire, release, LIMIT
from app.security import decrypt
from test_platform import process_all


def pdf_bytes(pages=2):
    pdf = fitz.open()
    for i in range(pages):
        pdf.new_page().insert_text((40, 40), f"Application page {i + 1}")
    data = pdf.tobytes()
    pdf.close()
    return data


def create_case(signed):
    from test_platform import publish_fixture

    publish_fixture(signed)
    branch = signed.get("/api/branches").json()[0]["id"]
    result = signed.post(
        "/api/uploads",
        data={"branch_id": branch, "template": "forex"},
        files=[("files", ("Rina_transaction.pdf", pdf_bytes(), "application/pdf"))],
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert result.status_code == 202, result.text
    with SessionLocal() as db:
        doc = db.scalar(
            select(Document).where(Document.case_id == result.json()["case_ids"][0])
        )
    return doc


def save_key(signed):
    r = signed.put("/api/connectors/spider-ai", json={"api_key": "test-spider-secret"})
    assert r.status_code == 200, r.text
    assert "test-spider-secret" not in r.text
    assert "test-spider-secret" not in signed.get("/api/connectors/spider-ai").text
    with SessionLocal() as db:
        item = db.scalar(select(SpiderConnector))
        assert item.encrypted != "test-spider-secret"
        assert decrypt(item.encrypted) == "test-spider-secret"


def test_image_only_calls_cache_and_existing_schema(signed, monkeypatch):
    save_key(signed)
    doc = create_case(signed)
    cfg = default_config()
    cfg["provider"] = "spider-ai"
    cfg['sequential_page_extraction'] = False
    cfg['profiles']['application']['classification_description']+=' CLASSIFICATION_SENTINEL'
    cfg["profiles"]["application"]["system_instruction"] = (
        "Use this custom System Instruction and supplied images only."
    )
    cfg["profiles"]["application"]["schema"]["properties"]["branch"]["description"] = (
        "SAVED_FIELD_DESCRIPTION"
    )
    calls = []

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, headers, json):
            calls.append(json)
            assert url == "https://spider.thantowijauhari.com/v1/chat/completions"
            assert headers["Authorization"] == "Bearer test-spider-secret"
            assert headers["Content-Type"] == "application/json"
            assert headers["Accept"] == "application/json"
            assert json["stream"] is False
            assert json["model"] == MODEL
            assert json["temperature"] == 0.41
            assert json["top_p"] == 0.22
            assert json["response_format"] == {"type": "json_object"}
            images = [
                p for p in json["messages"][1]["content"] if p["type"] == "image_url"
            ]
            assert len(images) == 2
            for item in images:
                encoded = item["image_url"]["url"].split(",", 1)[1]
                assert base64.b64decode(encoded).startswith(b"\xff\xd8")
            value = (
                {"type": "application", "confidence": 0.99}
                if len(calls) == 1
                else fixture_response("application")["extract_result"]
            )
            return httpx.Response(
                200,
                json={
                    "id": f"chat-{len(calls)}",
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {"content": __import__("json").dumps(value)},
                        }
                    ],
                },
            )

    monkeypatch.setattr("app.spider_provider.httpx.Client", Client)
    response, classification = run_provider(doc, cfg, lambda: None)
    assert classification["type"] == "application"
    assert 'CLASSIFICATION_SENTINEL' in __import__('json').dumps(calls[0]['messages'])
    assert (
        response["extract_result"] == fixture_response("application")["extract_result"]
    )
    assert "custom System Instruction" in calls[1]["messages"][0]["content"]
    assert (
        calls[1]["messages"][0]["content"]
        == __import__("app.extraction_prompts",fromlist=["system_instruction"]).system_instruction(cfg["profiles"]["application"])
    )
    extraction_text = __import__("json").dumps(calls[1]["messages"])
    assert "SAVED_FIELD_DESCRIPTION" in extraction_text
    assert "JSON Schema" not in extraction_text
    assert "Do not cross-reference other documents" in extraction_text
    from app.spider_provider import field_catalog

    catalog = field_catalog(cfg["profiles"]["application"]["schema"])
    assert catalog["beneficiary"]["name"] is None
    assert set(catalog) == set(cfg["profiles"]["application"]["schema"]["properties"])
    again, _ = run_provider(doc, cfg, lambda: None)
    assert again == response and len(calls) == 2
    # The cached response feeds the existing validation/report pipeline without a cloud call.
    with SessionLocal.begin() as db:
        case = db.get(Case, doc.case_id)
        db.get(Config, case.config_id).payload = cfg
        # Spider must ignore stale Llama parse artifacts even if they are unavailable.
        stored = db.get(Document, doc.id)
        stored.provider_state = {
            **stored.provider_state,
            "parse_response_key": "missing-llama-artifact",
        }
    process_all()
    updated = signed.get(f"/api/cases/{doc.case_id}").json()["documents"][0]
    assert updated["status"] == "COMPLETED"
    assert updated["raw"] == response["extract_result"]
    with SessionLocal.begin() as db:
        stored = db.get(Document, doc.id)
        stored.status = "ERROR"
        old_extract_key = stored.provider_state["spider_extract_response_key"]
        old_classify_key = stored.provider_state["spider_classify_response_key"]
    url = f"/api/documents/{doc.id}/spider-resubmit"
    assert (
        signed.post(
            url,
            json={
                "reason": "Use the revised minimal prompt",
                "accept_possible_duplicate_charge": False,
            },
        ).status_code
        == 409
    )
    assert (
        signed.post(
            url,
            json={
                "reason": "Use the revised minimal prompt",
                "accept_possible_duplicate_charge": True,
            },
        ).status_code
        == 202
    )
    with SessionLocal() as db:
        stored = db.get(Document, doc.id)
        assert (
            not stored.raw
            and "spider_extract_response_key" not in stored.provider_state
        )
        assert stored.provider_state["spider_classify_response_key"] == old_classify_key
    from app.storage import store

    assert store().read(old_extract_key)
    run_provider(stored, cfg, lambda: None)
    assert (
        len(calls) == 3
    )  # Only extraction is resubmitted; classification remains cached.


def test_stored_spider_result_skips_native_pipeline_and_preserves_types(
    signed, monkeypatch
):
    doc = create_case(signed)
    cfg = default_config()
    cfg["provider"] = "spider-ai"
    raw = fixture_response("application")["extract_result"]
    del raw["swift_code"]
    raw["beneficiary_account_number"] = 12345
    raw["to_name"] = {"complete": "true", "raw": "Observed name"}
    with SessionLocal.begin() as db:
        case = db.get(Case, doc.case_id)
        db.get(Config, case.config_id).payload = cfg
        stored = db.get(Document, doc.id)
        stored.raw = raw
        stored.metadata_json = {"provider": "spider-ai"}

    def forbidden(*args, **kwargs):
        raise AssertionError("Spider must not enter native normalization/validation")

    monkeypatch.setattr("app.processor.validate_extraction", forbidden)
    monkeypatch.setattr("app.processor.apply_evidence_review", forbidden)
    # No API key exists: process the cached model result without another cloud call.
    process_all()
    updated = signed.get(f"/api/cases/{doc.case_id}").json()["documents"][0]
    assert updated["status"] == "COMPLETED" and updated["error"] == ""
    assert updated["validation_status"] == "SKIPPED"
    assert updated["raw"] == raw and updated["normalized"] == raw
    assert "swift_code" not in updated["normalized"]
    assert updated["normalized"]["to_name"]["complete"] == "true"
    assert all(
        not f["issues"] and f["status"] == "SKIPPED"
        for f in updated["validation"]["fields"].values()
    )
    # Manual effective correction also bypasses the schema and leaves original data intact.
    result = signed.post(
        f"/api/documents/{doc.id}/effective-corrections",
        json={
            "field": "beneficiary_account_number",
            "expected_value": 12345,
            "value": "00012345",
            "reason": "Correct value from source image",
        },
    )
    assert result.status_code == 202, result.text
    process_all()
    updated = signed.get(f"/api/cases/{doc.case_id}").json()["documents"][0]
    assert updated["raw"]["beneficiary_account_number"] == 12345
    assert updated["normalized"]["beneficiary_account_number"] == "00012345"
    assert updated["validation_status"] == "SKIPPED"


def test_spider_accepts_model_formatted_freeform_result(signed, monkeypatch):
    import json
    from app.spider_provider import run_spider

    doc = create_case(signed)
    save_key(signed)
    doc.classification = {"manual": True, "type": "application"}
    result = {
        "section": {"name": "Observed name", "complete": "true"},
        "identifier": "00012345",
    }
    monkeypatch.setattr(
        "app.spider_provider.completion",
        lambda *a, **k: {
            "id": "chat-freeform",
            "choices": [
                {"finish_reason": "stop", "message": {"content": json.dumps(result)}}
            ],
        },
    )
    cfg = default_config()
    cfg['sequential_page_extraction'] = False
    cfg["provider"] = "spider-ai"
    response, _ = run_spider(doc, cfg, lambda: None)
    assert response["extract_result"] == result
    assert response["extract_metadata"]["document_validation_status"] == "SKIPPED"


@pytest.mark.parametrize("status", [200, 413, "sse"])
def test_http_error_or_non_json_body_is_preserved_with_request_preview(
    signed, monkeypatch, status
):
    import json
    from app.storage import store

    doc = create_case(signed)
    save_key(signed)
    cfg = default_config()
    cfg["provider"] = "spider-ai"

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, headers, json):
            if status == "sse":
                return httpx.Response(
                    200,
                    text="data: [DONE]\n\n",
                    headers={"content-type": "text/event-stream"},
                )
            return httpx.Response(
                status,
                text="<html>gateway response</html>",
                headers={"content-type": "text/html"},
            )

    monkeypatch.setattr("app.spider_provider.httpx.Client", Client)
    with pytest.raises(
        ProcessingIssue,
        match="request body too large"
        if status == 413
        else "SSE despite stream=false"
        if status == "sse"
        else "HTTP 200 response is not valid JSON",
    ):
        run_provider(doc, cfg, lambda: None)
    with SessionLocal() as db:
        state = db.get(Document, doc.id).provider_state
    assert state["spider_http_response"]["status"] == (
        200 if status == "sse" else status
    )
    assert store().read(state["spider_http_response"]["body_key"]) == (
        b"data: [DONE]\n\n" if status == "sse" else b"<html>gateway response</html>"
    )
    details = state["spider_request_details"]
    assert details["request_bytes"] > 0 and details["image_count"] == 2
    preview = store().read(details["preview_key"]).decode()
    assert "test-spider-secret" not in preview and "data:image" not in preview
    assert json.loads(preview)["temperature"] == 0.41
    assert bool(state.get("pending_create")) == (status != 413)


def test_missing_key_and_uncertain_submission_block_repayment(signed, monkeypatch):
    doc = create_case(signed)
    cfg = default_config()
    cfg["provider"] = "spider-ai"
    with pytest.raises(ProcessingIssue, match="API key"):
        run_provider(doc, cfg, lambda: None)
    save_key(signed)

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, *args, **kwargs):
            raise httpx.ReadTimeout("interrupted")

    monkeypatch.setattr("app.spider_provider.httpx.Client", Client)
    with pytest.raises(ProcessingIssue, match="uncertain"):
        run_provider(doc, cfg, lambda: None)
    with pytest.raises(ProcessingIssue, match="uncertain"):
        run_provider(doc, cfg, lambda: None)
    with SessionLocal.begin() as db:
        db.get(Document, doc.id).status = "ERROR"
    url = f"/api/documents/{doc.id}/spider-resubmit"
    assert (
        signed.post(
            url,
            json={
                "reason": "Explicit retry",
                "accept_possible_duplicate_charge": False,
            },
        ).status_code
        == 409
    )
    assert (
        signed.post(
            url,
            json={"reason": "Explicit retry", "accept_possible_duplicate_charge": True},
        ).status_code
        == 202
    )


def test_truncated_or_non_object_json_not_accepted():
    with pytest.raises(ValueError):
        content_json(
            {"choices": [{"finish_reason": "length", "message": {"content": "{}"}}]}
        )
    with pytest.raises(ValueError):
        content_json({"choices": [{"message": {"content": "[]"}}]})


@pytest.mark.parametrize("initial_type", ["riplay", "unknown"])
def test_riplay_single_page_calls_resume_and_combined_result(
    signed, monkeypatch, initial_type
):
    import re
    from app.storage import store, original_key

    doc = create_case(signed)
    save_key(signed)
    cfg = default_config()
    cfg["provider"] = "spider-ai"
    doc.doc_type = initial_type
    store().put(original_key(doc), pdf_bytes(4), "application/pdf")
    with SessionLocal.begin() as db:
        db.get(Document, doc.id).doc_type = initial_type
        db.get(Config, db.get(Case, doc.case_id).config_id).payload = cfg
    calls = []
    reject = [True]

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, headers, json):
            content = json["messages"][1]["content"]
            text = " ".join(part.get("text", "") for part in content)
            matched = re.search(r"physical page (\d+) of 4", text)
            page = int(matched[1]) if matched else 0
            assert sum(part['type']=='image_url' for part in content)==(1 if page else 2)
            calls.append(page)
            if page == 3 and reject[0]:
                reject[0] = False
                return httpx.Response(413, text="request too large")
            value = (
                {"type": "riplay", "confidence": 0.99}
                if page == 0
                else {
                    "customer_name": {
                        "raw": "Visible customer" if page == 4 else None,
                        "complete": True if page == 4 else None,
                    },
                    "customer_signature": {"present": page == 4, "page_number": page},
                    "document_date": "12-10-2026" if page == 4 else None,
                    "printed_date": "01-01-2025" if page == 2 else "01-01-2026",
                    "page_initials": {
                        "page_count": 4,
                        "pages": [{"page_number": page, "footer_present": page < 4}],
                    },
                }
            )
            return httpx.Response(
                200,
                json={
                    "id": f"chat-page-{page}",
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {"content": __import__("json").dumps(value)},
                        }
                    ],
                },
            )

    monkeypatch.setattr("app.spider_provider.httpx.Client", Client)
    with pytest.raises(ProcessingIssue, match="413"):
        run_provider(doc, cfg, lambda: None)
    assert calls == [0, 1, 2, 3]
    response, _ = run_provider(doc, cfg, lambda: None)
    assert calls == [0, 1, 2, 3, 3, 4]
    raw = response["extract_result"]
    assert [page["page_number"] for page in raw["page_results"]] == [1, 2, 3, 4]
    assert raw["customer_name"]["raw"] == "Visible customer"
    assert raw["customer_signature"] == {"present": True, "page_number": 4}
    assert raw["document_date"] == "12-10-2026"
    assert raw["printed_date"] is None
    assert any(
        c["field"] == "printed_date"
        for c in response["extract_metadata"]["page_merge_conflicts"]
    )
    assert [page["page_number"] for page in raw["page_initials"]["pages"]] == [
        1,
        2,
        3,
        4,
    ]
    assert len(response["extract_metadata"]["page_extractions"]) == 4
    assert run_provider(doc, cfg, lambda: None)[0] == response
    assert len(calls) == 6
    process_all()
    case = signed.get(f"/api/cases/{doc.case_id}").json()
    assert case["documents"][0]["status"] == "COMPLETED"
    assert case["documents"][0]["validation_status"] == "SKIPPED"
    assert case["documents"][0]["raw"] == raw
    # Explicit resubmission clears only the selected page, retaining all other pages.
    with SessionLocal.begin() as db:
        stored = db.get(Document, doc.id)
        stored.status = "ERROR"
        stored.provider_state = {
            **stored.provider_state,
            "provider_stage": "SPIDER_EXTRACT_PAGE_3",
        }
    result = signed.post(
        f"/api/documents/{doc.id}/spider-resubmit",
        json={
            "reason": "Re-extract only page three",
            "accept_possible_duplicate_charge": True,
        },
    )
    assert result.status_code == 202, result.text
    run_provider(doc, cfg, lambda: None)
    assert calls[-1] == 3 and len(calls) == 7


def test_riplay_legacy_cache_does_not_silently_repeat_paid_calls(signed, monkeypatch):
    import json
    from app.storage import store, original_key, object_key

    doc = create_case(signed)
    save_key(signed)
    doc.doc_type = "riplay"
    doc.classification = {"manual": True, "type": "riplay"}
    store().put(original_key(doc), pdf_bytes(4), "application/pdf")
    raw = {"customer_name": {"raw": "Existing observed customer"}}
    cached = {
        "id": "legacy-riplay-response",
        "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(raw)}}],
    }
    cached_key = object_key(
        doc.org, doc.branch_id, "documents", doc.id, "legacy-riplay-response.json"
    )
    store().put(cached_key, json.dumps(cached).encode(), "application/json")
    with SessionLocal.begin() as db:
        stored = db.get(Document, doc.id)
        stored.provider_state = {
            **stored.provider_state,
            "spider_extract_response_key": cached_key,
        }

    def forbidden(*args, **kwargs):
        raise AssertionError(
            "Legacy cached response must not create another paid request"
        )

    monkeypatch.setattr("app.spider_provider.httpx.Client", forbidden)
    cfg = default_config()
    cfg["provider"] = "spider-ai"
    response, _ = run_provider(doc, cfg, lambda: None)
    assert response["extract_result"] == raw
    assert response["id"] == "legacy-riplay-response"
    assert response['extract_metadata']['prompt_usage'][0]['status']=='LEGACY_OR_UNRECORDED'
    assert response['extract_metadata']['prompt_usage'][0]['manifest'] is None


def test_shared_capacity_limit_and_owner_scoping(client):
    initialize_slots()
    initialize_slots()
    owners = [str(uuid.uuid4()) for _ in range(75)]
    with ThreadPoolExecutor(max_workers=12) as pool:
        slots = list(pool.map(try_acquire, owners))
    occupied = [slot for slot in slots if slot is not None]
    assert len(occupied) == LIMIT and len(set(occupied)) == LIMIT
    assert try_acquire("extra") is None
    release(occupied[0], "wrong-owner")
    assert try_acquire("extra") is None
    owner = owners[slots.index(occupied[0])]
    release(occupied[0], owner)
    assert try_acquire("extra") == occupied[0]


def test_spider_configuration_and_credential_validation(signed):
    cfg = signed.get("/api/config").json()
    cfg["payload"]["provider"] = "spider-ai"
    assert (
        signed.post(
            "/api/config/publish",
            json={"expected_version": cfg["version"], "payload": cfg["payload"]},
        ).status_code
        == 200
    )
    assert (
        signed.put(
            "/api/connectors/spider-ai", json={"api_key": "Bearer secret"}
        ).status_code
        == 422
    )
    assert (
        signed.put(
            "/api/connectors/spider-ai", json={"base_url": "http://example.com/v1"}
        ).status_code
        == 422
    )


def test_system_instruction_workbook_roundtrip_and_old_template():
    import io
    from openpyxl import load_workbook
    from app.config_workbook import export_config, import_config

    cfg = default_config()
    cfg["provider"] = "spider-ai"
    cfg["profiles"]["application"]["system_instruction"] = (
        "Read handwriting only from this source document."
    )
    data = export_config(cfg)
    draft, errors = import_config(data, cfg)
    assert (
        not errors
        and draft["profiles"]["application"]["system_instruction"]
        == cfg["profiles"]["application"]["system_instruction"]
    )
    workbook = load_workbook(io.BytesIO(data))
    workbook["Document Profiles"].delete_cols(7)
    out = io.BytesIO()
    workbook.save(out)
    draft, errors = import_config(out.getvalue(), cfg)
    assert (
        not errors
        and draft["profiles"]["application"]["system_instruction"]
        == cfg["profiles"]["application"]["system_instruction"]
    )


def test_render_limit_and_expired_capacity_are_explicit(signed):
    from app.storage import store, original_key
    from app.spider_provider import render_pages
    from app.worker_capacity import LEASE_SECONDS

    doc = create_case(signed)
    store().put(original_key(doc), pdf_bytes(21), "application/pdf")
    with pytest.raises(ValueError, match="1–20"):
        render_pages(doc, lambda: None)
    initialize_slots()
    owner = "expired-owner"
    slot = try_acquire(owner, now=1)
    assert slot is not None
    reclaimed = try_acquire("new-owner", now=1 + LEASE_SECONDS + 1)
    assert reclaimed == slot
    release(slot, owner)
    from app.db import WorkerSlot

    with SessionLocal() as db:
        assert db.get(WorkerSlot, slot).owner == "new-owner"
