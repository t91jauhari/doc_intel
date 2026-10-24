"""Unit and acceptance tests for dynamic Valas 1 vs Valas 2 and flexible date comparison."""

from datetime import date
import pytest

from app.date_utils import compare_dates, parse_flexible_date
from app.valas_resolution import (
    get_case_valas_document,
    is_field_applicable_to_valas,
    resolve_valas_path,
)
from app.sop import evaluate, value_at


def test_flexible_date_parsing_various_formats():
    # ISO formats
    assert parse_flexible_date("2025-07-01") == date(2025, 7, 1)
    assert parse_flexible_date("2025/07/01") == date(2025, 7, 1)
    assert parse_flexible_date("2025.07.01") == date(2025, 7, 1)

    # Local Day-first formats
    assert parse_flexible_date("01-07-2025") == date(2025, 7, 1)
    assert parse_flexible_date("01/07/2025") == date(2025, 7, 1)
    assert parse_flexible_date("1/7/2025") == date(2025, 7, 1)

    # Textual Indonesian and English months
    assert parse_flexible_date("1 Juli 2025") == date(2025, 7, 1)
    assert parse_flexible_date("01-Juli-2025") == date(2025, 7, 1)
    assert parse_flexible_date("1 July 2025") == date(2025, 7, 1)

    # ISO timestamp with time component
    assert parse_flexible_date("2025-07-01T14:30:00") == date(2025, 7, 1)
    assert parse_flexible_date("2025-07-01 08:00:00") == date(2025, 7, 1)

    # Dict scalar structures from OCR
    assert parse_flexible_date({"raw": "2025/07/01", "complete": True}) == date(2025, 7, 1)


def test_flexible_date_comparisons():
    # User case: "2025-07-01" vs "2025/07/01"
    assert compare_dates("2025-07-01", "2025/07/01", op="date_equal") is True

    # Cross-format: ISO vs local DD-MM-YYYY
    assert compare_dates("2025-07-01", "01-07-2025", op="date_equal") is True
    assert compare_dates("2025/07/01", "01/07/2025", op="date_equal") is True
    assert compare_dates("01/07/2025", "1 Juli 2025", op="date_equal") is True

    # date_on_or_after
    assert compare_dates("2025-07-02", "2025/07/01", op="date_on_or_after") is True
    assert compare_dates("2025/07/01", "2025-07-01", op="date_on_or_after") is True
    assert compare_dates("2025/06/30", "2025-07-01", op="date_on_or_after") is False


def test_flexible_date_invalid_values():
    # Impossible calendar dates
    with pytest.raises(ValueError):
        parse_flexible_date("31-02-2025")
    with pytest.raises(ValueError):
        parse_flexible_date("2025-02-31")
    with pytest.raises(ValueError):
        parse_flexible_date("not-a-date")
    with pytest.raises(ValueError):
        parse_flexible_date("")
    with pytest.raises(ValueError):
        parse_flexible_date(None)


def test_valas_resolution_path_mapping():
    # Generic "valas" path on Valas 1
    p, ok, _ = resolve_valas_path("valas.customer_name", "valas_declaration_1")
    assert ok is True
    assert p == "valas_declaration_1.customer_name"

    # Generic "valas" path on Valas 2
    p, ok, _ = resolve_valas_path("valas.customer_name", "valas_declaration_2")
    assert ok is True
    assert p == "valas_declaration_2.customer_name"

    # Valas 1-only field on Valas 2 should be NOT applicable
    p, ok, msg = resolve_valas_path("valas.usage_purpose", "valas_declaration_2")
    assert ok is False
    assert "valas_declaration_2 does not contain field" in msg

    # Rule targeting valas_declaration_1 but customer uploaded Valas 2:
    # 1. Shared field (customer_name) should dynamically remap to valas_declaration_2
    p, ok, _ = resolve_valas_path("valas_declaration_1.customer_name", "valas_declaration_2")
    assert ok is True
    assert p == "valas_declaration_2.customer_name"

    # 2. Shared field (creation_date)
    p, ok, _ = resolve_valas_path("valas_declaration_1.creation_date", "valas_declaration_2")
    assert ok is True
    assert p == "valas_declaration_2.creation_date"

    # 3. Valas 1-only field (usage_purpose) should be marked NOT_APPLICABLE
    p, ok, msg = resolve_valas_path("valas_declaration_1.usage_purpose", "valas_declaration_2")
    assert ok is False
    assert "Valas 2 is the applicable uploaded declaration" in msg

    # Symmetrical: rule targeting valas_declaration_2 on Valas 1
    p, ok, _ = resolve_valas_path("valas_declaration_2.customer_name", "valas_declaration_1")
    assert ok is True
    assert p == "valas_declaration_1.customer_name"


def test_sop_evaluate_valas_dynamic_understanding():
    cfg = {
        "sop_rules": [
            {
                "id": "RULE_VALAS_NAME",
                "label": "Application remitter name must match Valas customer name",
                "enabled": True,
                "source_ref": "CUSTOM:1",
                "scope_basis": "SYSTEM",
                "report_category": "DATA_COMPLETION",
                "operator": "match_exact",
                "path": "application.remitter.name",
                "other_path": "valas_declaration_1.customer_name",
            },
            {
                "id": "RULE_VALAS_DATE",
                "label": "Application date must match Valas creation date across formats",
                "enabled": True,
                "source_ref": "CUSTOM:2",
                "scope_basis": "SYSTEM",
                "report_category": "DATA_COMPLETION",
                "operator": "date_equal",
                "path": "application.transaction_date",
                "other_path": "valas_declaration_1.creation_date",
            },
            {
                "id": "RULE_VALAS1_PURPOSE",
                "label": "Valas 1 usage purpose must match application",
                "enabled": True,
                "source_ref": "CUSTOM:3",
                "scope_basis": "SYSTEM",
                "report_category": "DATA_COMPLETION",
                "operator": "match_exact",
                "path": "valas_declaration_1.usage_purpose",
                "other_path": "application.transaction_purpose",
            },
        ],
        "report_mapping": {
            "DATA_COMPLETION": "DATA_COMPLETION",
            "CUSTOMER_SIGNATURE": "CUSTOMER_SIGNATURE",
            "DOCUMENT_COMPLETION": "DOCUMENT_COMPLETION",
            "OFFICER_REVIEW_APPROVAL": "OFFICER_REVIEW_APPROVAL",
        },
    }

    # Case 1: Customer uploaded valas_declaration_2 (NOT valas_declaration_1)
    docs = [
        {
            "id": "app_1",
            "doc_type": "application",
            "status": "COMPLETED",
            "normalized": {
                "remitter": {"name": "PT MAJU MUNDUR"},
                "transaction_date": "2025-07-01",  # ISO format
                "transaction_purpose": "Import machinery",
            },
        },
        {
            "id": "valas_2",
            "doc_type": "valas_declaration_2",
            "status": "COMPLETED",
            "normalized": {
                "customer_name": "PT MAJU MUNDUR",
                "creation_date": "2025/07/01",  # Format with slash!
                "currency": "USD",
            },
        },
    ]

    findings = {f["rule_id"]: f for f in evaluate(docs, cfg, {})}

    # RULE_VALAS_NAME should PASS because it dynamically mapped customer_name to valas_declaration_2!
    assert findings["RULE_VALAS_NAME"]["result"] == "PASS"

    # RULE_VALAS_DATE should PASS because "2025-07-01" equals "2025/07/01"!
    assert findings["RULE_VALAS_DATE"]["result"] == "PASS"

    # RULE_VALAS1_PURPOSE should be NOT_APPLICABLE because Valas 2 does not have usage_purpose!
    assert findings["RULE_VALAS1_PURPOSE"]["result"] == "NOT_APPLICABLE"


def test_sop_evaluate_date_comparisons_various_formats():
    cfg = {
        "sop_rules": [
            {
                "id": "RULE_DATE_EQUAL_1",
                "label": "Date comparison ISO vs slash",
                "enabled": True,
                "source_ref": "CUSTOM:1",
                "scope_basis": "SYSTEM",
                "report_category": "DATA_COMPLETION",
                "operator": "date_equal",
                "path": "doc_a.date_field",
                "other_path": "doc_b.date_field",
            },
            {
                "id": "RULE_DATE_EQUAL_2",
                "label": "Date comparison DD-MM-YYYY vs YYYY/MM/DD",
                "enabled": True,
                "source_ref": "CUSTOM:2",
                "scope_basis": "SYSTEM",
                "report_category": "DATA_COMPLETION",
                "operator": "date_equal",
                "path": "doc_a.date_field_2",
                "other_path": "doc_b.date_field_2",
            },
            {
                "id": "RULE_DATE_ON_OR_AFTER",
                "label": "Date on or after cross format",
                "enabled": True,
                "source_ref": "CUSTOM:3",
                "scope_basis": "SYSTEM",
                "report_category": "DATA_COMPLETION",
                "operator": "date_on_or_after",
                "path": "doc_a.date_field_3",
                "other_path": "doc_b.date_field_3",
            },
        ],
        "report_mapping": {
            "DATA_COMPLETION": "DATA_COMPLETION",
            "CUSTOMER_SIGNATURE": "CUSTOMER_SIGNATURE",
            "DOCUMENT_COMPLETION": "DOCUMENT_COMPLETION",
            "OFFICER_REVIEW_APPROVAL": "OFFICER_REVIEW_APPROVAL",
        },
    }

    docs = [
        {
            "id": "a",
            "doc_type": "doc_a",
            "status": "COMPLETED",
            "normalized": {
                "date_field": "2025-07-01",
                "date_field_2": "01-07-2025",
                "date_field_3": "2025/07/15",
            },
        },
        {
            "id": "b",
            "doc_type": "doc_b",
            "status": "COMPLETED",
            "normalized": {
                "date_field": "2025/07/01",
                "date_field_2": "2025/07/01",
                "date_field_3": "10-07-2025",
            },
        },
    ]

    findings = {f["rule_id"]: f for f in evaluate(docs, cfg, {})}
    assert findings["RULE_DATE_EQUAL_1"]["result"] == "PASS"
    assert findings["RULE_DATE_EQUAL_2"]["result"] == "PASS"
    assert findings["RULE_DATE_ON_OR_AFTER"]["result"] == "PASS"
