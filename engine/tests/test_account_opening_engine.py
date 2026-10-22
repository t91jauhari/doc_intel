"""Synthetic contract and validation tests, independent of workbook sample answers."""

import copy
import json
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from account_opening.profiles import NAMES, REFERENCE, get, validate, validate_policy


def inputs(name="account_opening_form"):
    schema = get(name)["schema"]
    raw = {
        key: {"present": None, "text": None, "complete": None, "evidence": None}
        if prop["type"] == "object"
        else None
        for key, prop in schema["properties"].items()
    }
    policy = json.loads((ROOT / get(name)["policy"]).read_text())
    meta = {
        "field_metadata": {
            "document_metadata": {key: {"confidence": 0.99} for key in raw}
        }
    }
    return raw, meta, policy


def result(changes, name="account_opening_form", policy_changes=None):
    raw, meta, policy = inputs(name)
    raw.update(changes)
    policy.update(policy_changes or {})
    return validate(name, raw, meta, policy, date(2026, 10, 8))


@pytest.mark.parametrize(
    "name,count",
    [
        ("join_visit", 16),
        ("edd", 39),
        ("account_opening_form", 93),
        ("signature_difference", 12),
        ("company_reference", 20),
    ],
)
def test_complete_contracts_preserve_raw_and_require_all_schema_keys(name, count):
    raw, meta, policy = inputs(name)
    original = copy.deepcopy(raw)
    report = validate(name, raw, meta, policy, date(2026, 10, 8))
    assert len(get(name)["schema"]["properties"]) == count
    assert report["raw"] == original and raw == original
    assert len(report["fields"]) == count
    raw.pop(next(iter(raw)))
    with pytest.raises(ValueError, match="missing fields"):
        validate(name, raw, meta, policy)


@pytest.mark.parametrize(
    "control,value,field,status",
    [
        ("existing_account", "Tidak", "existing_account_number", "NOT_APPLICABLE"),
        ("existing_account", "Ya", "existing_account_number", "FAIL"),
        ("existing_account", "unclear", "existing_account_number", "REVIEW"),
        ("citizenship", "WNI", "supporting_identity_number", "NOT_APPLICABLE"),
        ("citizenship", "WNA", "supporting_identity_number", "FAIL"),
        (
            "current_address_choice",
            "Sama dengan E-KTP",
            "current_address",
            "NOT_APPLICABLE",
        ),
        ("current_address_choice", "Berbeda", "current_address", "FAIL"),
    ],
)
def test_conditional_fields_do_not_guess_applicability(control, value, field, status):
    assert result({control: value})["fields"][field]["status"] == status


def test_date_time_identifiers_and_birth_text_are_readable_without_invention():
    report = result(
        {
            "identity_type": "E-KTP",
            "identity_number": "001234 5678901234",
            "existing_account": "Ya",
            "existing_account_number": "00-1234",
            "birth_place_date": "KOTA TEST, 1 Juni 1993",
            "identity_valid_until": "seumur hidup",
            "email": "Person@EXAMPLE.COM",
            "monthly_income": "s/dRp5 Juta",
        }
    )
    assert report["normalized"]["identity_number"] == "0012345678901234"
    assert report["normalized"]["existing_account_number"] == "001234"
    assert report["normalized"]["birth_place_date"] == "KOTA TEST, 01-06-1993"
    assert report["normalized"]["identity_valid_until"] == "SEUMUR HIDUP"
    assert report["normalized"]["email"] == "Person@example.com"
    assert report["fields"]["monthly_income"]["status"] == "PASS"
    report = result(
        {"confirmation_time": "9:05", "confirmation_date": "2025-06-10"},
        "company_reference",
    )
    assert report["normalized"]["confirmation_time"] == "09:05"
    assert report["normalized"]["confirmation_date"] == "10-06-2025"


def test_nested_enum_and_slash_phrases_are_preserved():
    assert (
        "Pemilik Manfaat(Beneficial Owner)"
        in next(
            f
            for f in REFERENCE["profiles"]["edd"]["fields"]
            if f["key"] == "person_type"
        )["enum_values"]
    )
    assert (
        result({"person_type": "Pemilik Manfaat(Beneficial Owner)"}, "edd")["fields"][
            "person_type"
        ]["status"]
        == "PASS"
    )
    assert (
        result({"residence_status": "Sewa/Kost"})["fields"]["residence_status"][
            "status"
        ]
        == "PASS"
    )


@pytest.mark.parametrize(
    "value,status",
    [("31-02-2025", "FAIL"), ("10-10-2026", "FAIL"), ("2025-06-10", "REVIEW")],
)
def test_invalid_future_and_unconfirmed_business_calendar(value, status):
    assert (
        result({"transaction_date": value})["fields"]["transaction_date"]["status"]
        == status
    )


def test_configurable_business_calendar_and_identity_expiry():
    assert (
        result(
            {"transaction_date": "10-06-2025"},
            policy_changes={"business_calendar_confirmed": True},
        )["fields"]["transaction_date"]["status"]
        == "PASS"
    )
    assert (
        result(
            {"transaction_date": "10-06-2025"},
            policy_changes={
                "business_calendar_confirmed": True,
                "business_holidays": ["2025-06-10"],
            },
        )["fields"]["transaction_date"]["status"]
        == "FAIL"
    )
    assert (
        result({"identity_valid_until": "01-01-2030"})["fields"][
            "identity_valid_until"
        ]["status"]
        == "PASS"
    )
    assert (
        result({"identity_valid_until": "01-01-2020"})["fields"][
            "identity_valid_until"
        ]["status"]
        == "FAIL"
    )


def test_unknown_enum_raw_is_retained_and_low_confidence_cannot_pass():
    raw, meta, policy = inputs()
    raw["gender"] = "unclear selection"
    raw["customer_name"] = "Synthetic Name"
    meta["field_metadata"]["document_metadata"]["customer_name"]["confidence"] = 0.5
    report = validate("account_opening_form", raw, meta, policy)
    assert report["normalized"]["gender"] == raw["gender"]
    assert report["fields"]["gender"]["status"] == "REVIEW"
    assert report["fields"]["customer_name"]["status"] == "REVIEW"


def test_visual_presence_is_not_stamp_authenticity_and_unknown_checkbox_is_not_selected():
    mark = {
        "present": True,
        "complete": True,
        "text": "COPY",
        "evidence": "visible page 1 stamp",
    }
    assert (
        result({"verification_stamp": mark})["fields"]["verification_stamp"]["status"]
        == "REVIEW"
    )
    for key in ("foreign_tax_obligation", "identity_copy_check", "npwp_copy_check"):
        assert result({})["fields"][key]["status"] == "NOT_APPLICABLE"


def test_invalid_policy_cannot_publish_or_run():
    _, _, policy = inputs()
    policy["conditional_rules"]["existing_account_number"]["field"] = "unregistered"
    with pytest.raises(ValueError):
        validate_policy("account_opening_form", policy)
