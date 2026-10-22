import csv
import io
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.dataset_comparison import DATASET, canonical, compare, number
from app.db import Document, SessionLocal, User
from test_platform import upload


def document(kind="ektp", normalized=None, id="doc"):
    return SimpleNamespace(id=id, filename=f"{id}.pdf", doc_type=kind, status="COMPLETED", normalized=normalized or {}, validation={}, provider_state={"extract_job_id": "ext"}, raw={"name": "wrong OCR value"}, overrides={"name": "not yet validated"})


def results(docs, edits=None):
    value = compare(SimpleNamespace(id="case", customer="Customer"), docs, {"sample_id": "1", "revision": 1, "edits": edits or {}})
    return value, {r["id"]: r for r in value["rows"]}


def test_dataset_coverage_and_explicit_schema_gaps():
    assert len(DATASET["samples"]) == 10
    assert len(DATASET["rows"]) == 163
    mapping = {r["id"]: r["field"] for r in DATASET["rows"]}
    assert mapping["row-148"] == 'stamp_verification'
    assert mapping["row-199"] is None  # Redundant LLD Value Transaksi.
    assert mapping["row-200"] == "transaction_value"
    assert mapping["row-110"] == "beneficiary_account_number"
    assert mapping["row-50"] == 'ship_to_name'


def test_field_reprocess_observations_compare_without_rewriting_raw():
    from app.dataset_comparison import project,effective_canonical
    doc=document(normalized={'name':{'raw':'Printed name','complete':True},'nik':{'raw':'000 123','complete':True}})
    assert project(doc,'name','text')=='Printed name'
    assert canonical(project(doc,'nik','identifier'),'identifier','nik')=='000123'
    assert doc.normalized['nik']['raw']=='000 123'
    doc=document('riplay',{'page_initials':{'page_count':4,'pages':[{'page_number':i,'footer_present':i<4} for i in range(1,5)]}})
    assert project(doc,'page_initials','initials') is False


def test_only_effective_values_compare_and_partial_coverage_is_visible():
    result, rows = results([document(normalized={"name": "  indah LARUNA prima ", "nik": "3896872710880099", "birth_date": "27-10-1988", "rt": "011", "owner_signature": {"present": None}})])
    assert rows["row-4"]["status"] == "MATCH"
    assert rows["row-3"]["status"] == "MATCH"
    assert rows["row-6"]["status"] == "MATCH"
    assert rows["row-20"]["status"] == "REVIEW"
    assert result["summary"]["complete"] is False
    assert result["result"] == "REVIEW"
    _, changed = results([document(normalized={"nik": "3896872710880098"})])
    assert changed["row-3"]["status"] == "MISMATCH"
    assert canonical("00123", "identifier") != canonical("123", "identifier")
    assert canonical("4", "identifier", "rt") == "004"


def test_amounts_keep_decimal_currency_and_ambiguity():
    assert number("USD 1,234.50") == ("USD", "1234.5")
    assert number("Rp 1.234,50") == ("IDR", "1234.5")
    for value in ["59.765", "59,765", "$50", "USD [BLANK]", "NaN"]:
        with pytest.raises(ValueError):
            number(value)
    edit = {"row-91": {"value": "CNY 3248"}, "row-93": {"value": "CNY 3248"}}
    result, rows = results([document("application", {"amount": "3248", "total_amount": "3248", "currency": "CNY"})], edit)
    assert rows["row-91"]["status"] == "MATCH"
    assert rows["row-93"]["status"] == "MATCH"
    _, rows = results([document("application", {"amount": "3248", "currency": "USD"})], edit)
    assert rows["row-91"]["status"] == "REVIEW"
    assert rows["row-93"]["status"] == "UNMAPPED"


def test_duplicate_documents_pending_and_json_reference():
    _, rows = results([document(id="one"), document(id="two")])
    assert rows["row-4"]["status"] == "REVIEW"
    doc = document("application", {"beneficiary": {"name": "TEST", "address": "ADDRESS", "phone": "001"}})
    _, rows = results([doc])
    assert rows["row-79"]["status"] == "REVIEW"
    _, rows = results([doc], {"row-79": {"value": {"name": "TEST", "address": "ADDRESS", "phone": "001"}}})
    assert rows["row-79"]["status"] == "MATCH"
    doc.status = "QUEUED"
    _, rows = results([doc])
    assert rows["row-79"]["status"] == "PENDING"
    assert rows["row-104"]["status"] == "NOT_APPLICABLE"


def test_presence_uses_stamp_observation_and_reference_edits_do_not_mask_uncertainty():
    _, rows = results([document("application", {"bank_approval": {"present": True, "stamp_present": False}})])
    assert rows["row-97"]["effective_value"] is False
    doc = document("riplay", {"page_initials": {"pages": [{"page_number": 1, "footer_present": True}, {"page_number": 2, "footer_present": True}]}})
    _, rows = results([doc], {"row-36": {"value": True}})
    assert rows["row-36"]["status"] == "REVIEW"
    doc.normalized["page_initials"]["pages"].append({"page_number": 3, "footer_present": False})
    _, rows = results([doc], {"row-36": {"value": True}})
    assert rows["row-36"]["status"] == "MISMATCH"


def test_case_comparison_edits_exports_and_permissions(signed):
    assert signed.get("/api/dataset-sample").status_code == 200
    batch = upload(signed, names=("Indah Laruna Prima_ektp.pdf",)).json()
    case_id = batch["case_ids"][0]
    url = f"/api/cases/{case_id}/comparison"
    assert signed.get(url).json()["result"] == "NOT_CONFIGURED"
    assert signed.get(url + "/export").status_code == 409
    with SessionLocal.begin() as db:
        doc = db.scalar(select(Document).where(Document.case_id == case_id))
        doc.doc_type = "ektp"
        doc.status = "COMPLETED"
        doc.normalized = {"name": "INDAH LARUNA PRIMA", "nik": "3896872710880099"}
        doc.raw = {"name": "WRONG RAW VALUE"}
        doc_id = doc.id
    payload = {"sample_id": "1", "expected_revision": 0, "documents": {"2": doc_id}, "reason": "Selected dataset sample"}
    saved = signed.put(url, json=payload)
    assert saved.status_code == 200, saved.text
    assert saved.json()["revision"] == 1
    assert signed.put(url, json=payload).status_code == 409
    payload.update(expected_revision=1, edits={"row-4": "=FORMULA TEST"}, reason="Corrected reference name")
    saved = signed.put(url, json=payload)
    assert saved.status_code == 200
    row = next(r for r in saved.json()["rows"] if r["id"] == "row-4")
    assert row["status"] == "MISMATCH" and row["original_value"] == "INDAH LARUNA PRIMA"
    assert row["edited"] and row["edit"]["reason"] == "Corrected reference name"
    exported = signed.get(url + "/export?format=csv")
    assert exported.status_code == 200
    rows = list(csv.DictReader(io.StringIO(exported.content.decode("utf-8-sig"))))
    row = next(r for r in rows if r["field"] == "name")
    assert row["dataset_value"] == "'=FORMULA TEST"
    assert row["effective_value"] == "INDAH LARUNA PRIMA"
    assert row["source"] == "effective_normalized"
    snapshot = signed.get(url + "/export?format=json").json()
    assert snapshot["revision"] == 2 and snapshot["fingerprint"] == saved.json()["fingerprint"]
    assert signed.get(url + "/export?format=xlsx").status_code == 422
    payload.update(expected_revision=2, documents={"169": doc_id})
    assert signed.put(url, json=payload).status_code == 422
    other = upload(signed, names=("Other Customer_ektp.pdf",), key="other-reference-case").json()["case_ids"][0]
    with SessionLocal.begin() as db:
        outsider = db.scalar(select(Document).where(Document.case_id == other))
        outsider.doc_type = "ektp"
        outsider_id = outsider.id
    assert signed.put(url, json={**payload, "documents": {"2": outsider_id}, "edits": {}}).status_code == 422
    payload.update(documents={"2": doc_id}, edits={"unknown-row": "test"})
    assert signed.put(url, json=payload).status_code == 422
    with SessionLocal() as db:
        assert db.get(Document, doc_id).raw == {"name": "WRONG RAW VALUE"}
        assert db.get(Document, doc_id).normalized["name"] == "INDAH LARUNA PRIMA"
    identity = signed.get("/api/auth/session").json()["user"]
    with SessionLocal.begin() as db:
        db.get(User, identity["id"]).role = "auditor"
    assert signed.get(url).status_code == 200
    assert signed.put(url, json={**payload, "edits": {}}).status_code == 403
    with SessionLocal.begin() as db:
        db.get(User, identity["id"]).org = "another-organization"
    assert signed.get(url).status_code == 404
    assert signed.get(url + "/export?format=json").status_code == 404
    signed.cookies.clear()
    assert signed.get(url).status_code == 401
