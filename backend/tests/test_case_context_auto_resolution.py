"""
Tests for automated Case Context and Transaction Metadata resolution.
Ensures straight-through processing (STP) for SOP evaluation while respecting officer overrides.
"""
import pytest
from sqlalchemy import select
from app.db import Base, SessionLocal, engine, Case, Document, CaseContext
from app.configuration.initialize import initialize_development
from app.case_context import (
    suggestions,
    resolve_case_context,
    ensure_case_context,
)
from app.case_processing import inputs


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(engine)
    initialize_development()
    yield


def test_resolve_forex_valas_format_2_and_matching_invoice():
    """Case with Application, EKTP, Valas Declaration 2, and matching Invoice."""
    docs = [
        {
            "id": "doc-app-1",
            "doc_type": "application",
            "status": "COMPLETED",
            "filename": "Aplikasi_Transaksi.pdf",
            "normalized": {
                "amount": "10000",
                "currency": "USD",
                "source_of_funds": "IDR",
                "customer_name": "Bayu Birdless",
            },
        },
        {
            "id": "doc-ektp-1",
            "doc_type": "ektp",
            "status": "COMPLETED",
            "filename": "EKTP.pdf",
            "normalized": {
                "nik": "3171012345670001",
                "name": "Bayu Birdless",
            },
        },
        {
            "id": "doc-valas-2",
            "doc_type": "valas_declaration_2",
            "status": "COMPLETED",
            "filename": "Pernyataan_Valas_Format_2.pdf",
            "normalized": {
                "customer_name": "Bayu Birdless",
                "currency": "USD",
            },
        },
        {
            "id": "doc-inv-1",
            "doc_type": "invoice",
            "status": "COMPLETED",
            "filename": "Invoice.pdf",
            "normalized": {
                "final_total_amount": {"amount_raw": "10000.00", "currency_raw": "$"},
                "claim_note": None,
            },
        },
    ]

    result = resolve_case_context(docs)
    values = result["values"]

    assert values["threshold_state"] == "WITHIN"
    assert values["customer_type"] == "INDIVIDUAL"
    assert values["identity_type"] == "NIK"
    assert values["transaction_direction"] == "IDR_TO_FOREIGN"
    assert values["payment_basis"] == "FULL_INVOICE"
    assert values["account_signature_difference"] == "NO"
    assert values["transaction_carrier"] == "CUSTOMER"
    assert values["application_document_id"] == "doc-app-1"
    assert values["declaration_document_id"] == "doc-valas-2"
    assert values["invoice_document_id"] == "doc-inv-1"
    assert result["annotation"]["actor"] == "system.auto_inference"


def test_resolve_partial_payment_and_valas_format_1():
    """Case with Valas 1 (>100k) and partial payment invoice."""
    docs = [
        {
            "id": "doc-app-2",
            "doc_type": "application",
            "status": "COMPLETED",
            "filename": "Slip_Aplikasi.pdf",
            "normalized": {
                "amount": "29200",
                "currency": "USD",
                "customer_name": "Sri Pujianty",
            },
        },
        {
            "id": "doc-valas-1",
            "doc_type": "valas_declaration_1",
            "status": "COMPLETED",
            "filename": "Pernyataan_Valas_Format_1.pdf",
            "normalized": {},
        },
        {
            "id": "doc-inv-2",
            "doc_type": "invoice",
            "status": "COMPLETED",
            "filename": "Commercial_Invoice.pdf",
            "normalized": {
                "final_total_amount": {"amount_raw": "59.765,00", "currency_raw": "$"},
            },
        },
    ]

    result = resolve_case_context(docs)
    values = result["values"]

    assert values["threshold_state"] == "ABOVE"
    assert values["payment_basis"] == "PARTIAL_PAYMENT"
    assert values["partial_payment_amount"] == "29200"
    assert values["partial_payment_currency"] == "USD"
    assert values["declaration_document_id"] == "doc-valas-1"
    assert values["invoice_document_id"] == "doc-inv-2"


def test_resolve_conflicting_valas_declarations():
    """When both Valas 1 and 2 are present, fails safe to UNKNOWN with conflict flag."""
    docs = [
        {
            "id": "v1",
            "doc_type": "valas_declaration_1",
            "status": "COMPLETED",
            "filename": "Valas_1.pdf",
        },
        {
            "id": "v2",
            "doc_type": "valas_declaration_2",
            "status": "COMPLETED",
            "filename": "Valas_2.pdf",
        },
    ]

    suggs = suggestions(docs)
    thresh = next((s for s in suggs if s["field"] == "threshold_state"), None)
    assert thresh is not None
    assert thresh["value"] == "UNKNOWN"
    assert thresh["conflict"] is True
    assert thresh["requires_acceptance"] is True


def test_ensure_case_context_db_persistence_and_respect_officer_override():
    """ensure_case_context writes to DB and never overwrites human annotations."""
    from app.db import Config
    with SessionLocal.begin() as db:
        cfg = db.scalar(select(Config))
        case = Case(
            org="sqe",
            branch_id="test-branch",
            template="forex",
            customer="Stuart",
            reference="REF-001",
            created_by="user-admin",
            config_id=cfg.id if cfg else "cfg-1",
        )
        db.add(case)
        db.flush()

        doc = Document(
            org="sqe",
            branch_id="test-branch",
            case_id=case.id,
            batch_id="batch-1",
            sha256="fake-sha256",
            doc_type="valas_declaration_2",
            status="COMPLETED",
            filename="Valas2.pdf",
            normalized={"customer_name": "Stuart Starshine"},
        )
        db.add(doc)
        case_id = case.id

    with SessionLocal.begin() as db:
        ctx = ensure_case_context(db, case_id)
        assert ctx is not None
        assert ctx.payload["threshold_state"] == "WITHIN"
        assert ctx.payload["annotation"]["actor"] == "system.auto_inference"

        # Now simulate a human officer manual override
        ctx.payload["threshold_state"] = "ABOVE"
        ctx.payload["annotation"] = {
            "actor": "user-officer-123",
            "reason": "Customer updated transaction above threshold",
            "evidence": "Addendum document page 2",
        }

    # Call ensure_case_context again; human annotation must be preserved
    with SessionLocal.begin() as db:
        ctx_recheck = ensure_case_context(db, case_id)
        assert ctx_recheck.payload["threshold_state"] == "ABOVE"
        assert ctx_recheck.payload["annotation"]["actor"] == "user-officer-123"
