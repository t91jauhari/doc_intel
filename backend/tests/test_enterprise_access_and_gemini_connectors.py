"""Acceptance and unit tests for Dual-Axis Access Control and Multi-Provider AI Connectors."""

import pytest
from app.gemini_provider import normalize_gemini_json
from app.extraction.connector_contracts import (
    GeminiOptions,
    GeminiConnectorInput,
    normalized_options,
    defaults,
)
from app.application.administration import (
    DEFAULT_ROLE_PERMISSIONS,
    DEFAULT_MENUS,
)


def test_gemini_connector_contracts_defaults_and_options():
    gemini_defaults = defaults("gemini")
    assert gemini_defaults["model_id"] == "gemini-2.5-pro"
    assert "https://generativelanguage.googleapis.com" in gemini_defaults["base_url"]

    opts = normalized_options("gemini", {"model_id": "gemini-flash-3.8", "temperature": 0.2})
    assert opts["model_id"] == "gemini-flash-3.8"
    assert opts["temperature"] == 0.2
    assert opts["top_p"] == 0.95


def test_gemini_response_normalization_zero_breakage():
    # Case 1: Standard structured response with extract_result
    raw_1 = """{
        "extract_result": {
            "customer_name": "PT BANK MEGA",
            "identity_number": "1234567890123456"
        },
        "classification": {
            "doc_type": "ektp",
            "confidence": 0.99
        },
        "_field_locations": {
            "customer_name": [100, 200, 150, 400]
        }
    }"""
    res, cls, locs = normalize_gemini_json(raw_1)
    assert res["customer_name"] == "PT BANK MEGA"
    assert cls["doc_type"] == "ektp"
    assert "customer_name" in locs

    # Case 2: Markdown wrapped ```json ... ```
    raw_markdown = """```json
    {
        "extract_result": {
            "amount": "1000.00",
            "currency": "USD"
        }
    }
    ```"""
    res, cls, locs = normalize_gemini_json(raw_markdown)
    assert res["amount"] == "1000.00"
    assert res["currency"] == "USD"

    # Case 3: Flat dictionary (direct field mapping without outer wrapper)
    raw_flat = """{
        "to_name": "PT SUPPLIER UTAMA",
        "invoice_number": "INV-2026-001",
        "final_total_amount": {"amount": "50000.00", "currency": "USD"}
    }"""
    res, cls, locs = normalize_gemini_json(raw_flat)
    assert res["to_name"] == "PT SUPPLIER UTAMA"
    assert res["invoice_number"] == "INV-2026-001"
    assert res["final_total_amount"]["amount"] == "50000.00"


def test_default_role_permissions_matrix():
    assert "bank_admin" in DEFAULT_ROLE_PERMISSIONS
    assert "branch_admin" in DEFAULT_ROLE_PERMISSIONS
    assert "reviewer" in DEFAULT_ROLE_PERMISSIONS
    assert "officer" in DEFAULT_ROLE_PERMISSIONS
    assert "auditor" in DEFAULT_ROLE_PERMISSIONS

    # Bank Admin has full settings and user management
    assert DEFAULT_ROLE_PERMISSIONS["bank_admin"]["can_edit_settings"] is True
    assert DEFAULT_ROLE_PERMISSIONS["bank_admin"]["can_manage_users"] is True

    # Auditor has read-only access to cases and reports, but not upload or settings
    assert "reports" in DEFAULT_ROLE_PERMISSIONS["auditor"]["menus"]
    assert "cases" in DEFAULT_ROLE_PERMISSIONS["auditor"]["menus"]
    assert "upload" not in DEFAULT_ROLE_PERMISSIONS["auditor"]["menus"]
    assert "settings" not in DEFAULT_ROLE_PERMISSIONS["auditor"]["menus"]
    assert DEFAULT_ROLE_PERMISSIONS["auditor"]["can_edit_settings"] is False

    # Reviewer can review/override cases but cannot edit settings or manage users
    assert DEFAULT_ROLE_PERMISSIONS["reviewer"]["can_override_cases"] is True
    assert DEFAULT_ROLE_PERMISSIONS["reviewer"]["can_edit_settings"] is False


def test_dual_axis_menu_intersection():
    # Role allows: overview, inbox, cases, reports, upload
    role_menus = set(["overview", "inbox", "cases", "reports", "upload"])
    
    # KCP Branch allows only: overview, inbox, cases, upload (no reports/kertas-kerja)
    kcp_branch_menus = set(["overview", "inbox", "cases", "upload"])

    # Effective menus for user in KCP branch
    effective_kcp = role_menus.intersection(kcp_branch_menus)
    assert "reports" not in effective_kcp
    assert "cases" in effective_kcp
    assert "upload" in effective_kcp

    # KCU Branch allows reports
    kcu_branch_menus = set(["overview", "inbox", "cases", "reports", "upload"])
    effective_kcu = role_menus.intersection(kcu_branch_menus)
    assert "reports" in effective_kcu
