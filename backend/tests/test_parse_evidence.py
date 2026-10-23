import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from app.parse_evidence import parse_box, link_parse_evidence
from app.provider_errors import api_diagnostic


def page():
    return {"page_number": 4, "page_width": 600, "page_height": 800}


def test_point_coordinates_and_rotation():
    box = parse_box([{"x": 60, "y": 80, "w": 120, "h": 80}], page(), "test")
    assert box["bbox"] == [0.1, 0.1, 0.3, 0.2]
    rotated = parse_box(
        [{"x": 60, "y": 80, "w": 120, "h": 80, "r": 90}], page(), "test"
    )
    assert rotated["bbox"] == pytest.approx([80 / 600, 60 / 800, 160 / 600, 180 / 800])


def test_supplied_sample_does_not_crop_logo_or_label_as_signature():
    parsed = json.loads(
        (Path(__file__).parents[1] / "fixtures/parse_bbox_sample.json").read_text()
    )
    links, candidates = link_parse_evidence({"customer_signature": True}, parsed)
    assert "customer_signature" not in links
    assert candidates["customer_signature"][0]["error"] == "Region has no Parse box"
    assert len(candidates["customer_signature"]) == 1


def test_unique_form_region_crops_but_requires_link_review():
    p = page()
    p["forms"] = [
        {
            "json_": [
                {
                    "type": "field",
                    "field": "signature",
                    "label": "Tanda Tangan Nasabah",
                    "bbox": [{"x": 300, "y": 600, "w": 120, "h": 80}],
                }
            ]
        }
    ]
    links, candidates = link_parse_evidence(
        {"customer_signature": {"present": True, "page_number": 4}},
        {"forms": {"pages": [p]}},
    )
    assert links["customer_signature"]["bbox"] == [0.5, 0.75, 0.7, 0.85]
    assert links["customer_signature"]["link_review_required"] is True
    p["forms"][0]["json_"].append(
        {
            "type": "field",
            "label": "Customer signature",
            "bbox": [{"x": 50, "y": 600, "w": 120, "h": 80}],
        }
    )
    assert not link_parse_evidence(
        {"customer_signature": True}, {"forms": {"pages": [p]}}
    )[0]


def test_initials_are_constrained_to_page_and_bottom_right():
    p = {
        **page(),
        "page_number": 2,
        "items": [
            {
                "type": "image",
                "caption": "paraf nasabah",
                "bbox": [{"x": 500, "y": 740, "w": 60, "h": 40}],
            }
        ],
    }
    raw = {
        "page_initials": {
            "pages": [{"page_number": n, "footer_present": True} for n in range(1, 4)]
        }
    }
    links, _ = link_parse_evidence(raw, {"items": {"pages": [p]}})
    assert set(links) == {"page_initials.pages.1"}
    p["items"][0]["bbox"][0]["x"] = 50
    assert not link_parse_evidence(raw, {"items": {"pages": [p]}})[0]


def test_diagnostic_omits_input_and_credentials():
    exc = SimpleNamespace(
        status_code=400,
        request_id="req-test",
        request=SimpleNamespace(
            url="https://api.cloud.llamaindex.ai/api/v2/extract?secret=x"
        ),
        body={
            "detail": [
                {
                    "loc": ["body", "configuration", "data_schema"],
                    "msg": "Invalid schema",
                    "input": {"api_key": "llx-secret", "customer": "private"},
                }
            ]
        },
    )
    result = api_diagnostic(exc, "EXTRACTING")
    assert result["endpoint"] == "/api/v2/extract" and result["stage"] == "EXTRACTING"
    assert (
        "Invalid schema" in result["detail"]
        and "private" not in result["detail"]
        and "llx-secret" not in result["detail"]
    )


def test_bad_request_records_stage_endpoint_and_detail(signed, monkeypatch, caplog):
    import httpx
    from llama_cloud import BadRequestError
    from app.provider import checkpoint
    from test_platform import upload, process_all

    def reject(doc, cfg, heartbeat):
        checkpoint(doc.id, provider_stage="EXTRACTING")
        request = httpx.Request(
            "POST", "https://api.cloud.llamaindex.ai/api/v2/extract"
        )
        raise BadRequestError(
            "Invalid schema",
            response=httpx.Response(400, request=request),
            body={
                "detail": [
                    {
                        "loc": ["configuration", "data_schema"],
                        "msg": "Unsupported keyword",
                        "input": "private document contents",
                    }
                ]
            },
        )

    monkeypatch.setattr("app.processor.run_provider", reject)
    cid = upload(
        signed, names=("diagnostic_transaction.pdf",), template="custom"
    ).json()["case_ids"][0]
    process_all()
    doc = signed.get(f"/api/cases/{cid}").json()["documents"][0]
    assert doc["status"] == "ERROR"
    assert "Unsupported keyword" in doc["error"] and "EXTRACTING" in doc["error"]
    assert doc["provider_state"]["provider_error"]["endpoint"] == "/api/v2/extract"
    assert "private document contents" not in caplog.text
