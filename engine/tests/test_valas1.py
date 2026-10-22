"""Synthetic Valas 1 rule and export scenarios; no live document extraction."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run
from valas1.schema import COLUMNS, SCHEMA
from valas1.validation import validate
from test_valas2 import evidence as common_evidence, verified_context

ROOT = Path(__file__).resolve().parents[1]


def evidence():
    shared = common_evidence()
    values = {k: deepcopy(shared[k]) for k, _ in COLUMNS if k in shared}
    values.update({
        "identity_number": {"raw": " 0001234567890123 ", "complete": True},
        "npwp": {"raw": "01.234.567.8-901.234", "complete": True, "available": True},
        "usage_purpose": {"raw": " Pembayaran kontrak peralatan ", "complete": True},
        "usage_date": "7 Agustus 2025", "usage_amount": {"amount_raw": "150.000,50", "currency_raw": "usd"},
        "receipt_source": {"raw": "Pendapatan usaha", "complete": True}, "receipt_date": "06-08-2025",
        "receipt_amount": {"amount_raw": "200.000,00", "currency_raw": "EUR"},
    })
    return {k: values[k] for k, _ in COLUMNS}


def metadata():
    return {"field_metadata": {"document_metadata": {k: {"confidence": .99} for k, _ in COLUMNS}}}


class Valas1Tests(unittest.TestCase):
    def setUp(self):
        self.raw = evidence()
        self.policy = run.read(ROOT / "valas1/policy.json")
        self.policy.update(identity_rule_confirmed=True, identity_required=True, identity_pattern=r"[0-9]{16}")
        self.context = verified_context(job="ext-synthetic-valas1")
        self.meta = metadata()

    def validate(self):
        return validate(self.raw, self.meta, self.policy, date(2026, 10, 5),
                        validation_context=self.context, extract_job_id="ext-synthetic-valas1")

    def codes(self, field, report=None):
        return [i["code"] for i in (report or self.validate())["fields"][field]["issues"]]

    def test_sixteen_fields_in_requested_order_and_correct_profile(self):
        report = self.validate()
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(len(COLUMNS), 16)
        self.assertEqual(list(SCHEMA["properties"]), [k for k, _ in COLUMNS])
        self.assertEqual(report["document_type"], "valas_declaration_1")
        self.assertNotIn("currency", report["normalized"])
        self.assertNotIn("stamp_verification", report["fields"])
        self.assertEqual([k for k, _ in COLUMNS][-4:], ["signatory_signature", "stamp_duty", "signatory", "signatory_company"])

    def test_usage_receipt_amounts_currencies_and_dates_remain_separate(self):
        report = self.validate()
        self.assertEqual(report["normalized"]["usage_amount"], {"amount": Decimal("150000.50"), "currency": "USD"})
        self.assertEqual(report["normalized"]["receipt_amount"], {"amount": Decimal("200000.00"), "currency": "EUR"})
        self.assertEqual(report["normalized"]["usage_date"], "07-08-2025")
        self.assertEqual(report["normalized"]["receipt_date"], "06-08-2025")
        self.assertEqual(report["normalized"]["creation_date"], "05-10-2026")
        self.assertEqual(report["raw"]["usage_amount"]["amount_raw"], "150.000,50")

    def test_default_unspecified_identity_rule_requires_review(self):
        self.policy = run.read(ROOT / "valas1/policy.json")
        self.assertIn("IDENTITY_RULE_NOT_CONFIGURED", self.codes("identity_number"))
        self.assertEqual(self.validate()["normalized"]["identity_number"], "0001234567890123")
        self.raw["identity_number"]["raw"] = None
        self.assertEqual(self.validate()["fields"]["identity_number"]["status"], "REVIEW")

    def test_configured_identity_format_required_optional_and_no_padding(self):
        self.raw["identity_number"]["raw"] = "123"
        self.assertIn("INVALID_IDENTITY_FORMAT", self.codes("identity_number"))
        self.assertEqual(self.validate()["normalized"]["identity_number"], "123")
        self.raw["identity_number"]["raw"] = None
        self.assertIn("REQUIRED", self.codes("identity_number"))
        self.policy["identity_required"] = False
        self.assertEqual(self.validate()["fields"]["identity_number"]["status"], "NOT_PRESENT")
        self.raw["identity_number"]["raw"] = "ABC-001/25"
        self.policy["identity_pattern"] = r"[A-Za-z0-9/-]+"
        self.assertEqual(self.validate()["fields"]["identity_number"]["status"], "PASS")

    def test_identity_pattern_missing_invalid_and_truncated_evidence(self):
        self.policy["identity_pattern"] = None
        self.assertIn("IDENTITY_FORMAT_RULE_NOT_CONFIGURED", self.codes("identity_number"))
        self.policy["identity_pattern"] = "["
        with self.assertRaises(ValueError): self.validate()
        self.policy["identity_pattern"] = r"[0-9]{16}"
        self.raw["identity_number"]["complete"] = False
        self.assertEqual(self.validate()["fields"]["identity_number"]["status"], "FAIL")

    def test_npwp_formatted_compact_and_nik_style_preserve_leading_zeros(self):
        for value, expected in [("01.234.567.8-901.234", "012345678901234"),
                                ("012345678901234", "012345678901234"), ("0001234567890123", "0001234567890123")]:
            with self.subTest(value=value):
                self.raw["npwp"]["raw"] = value
                self.assertEqual(self.validate()["fields"]["npwp"]["status"], "PASS")
                self.assertEqual(self.validate()["normalized"]["npwp"], expected)
        self.assertEqual(self.validate()["normalized"]["identity_number"], "0001234567890123")

    def test_npwp_malformed_non_numeric_incorrect_length_and_separators_fail(self):
        for value in ["01.234.567.8/901.234", "01-234-567-8-901-234", "NPWP 01.234.567.8-901.234",
                      "01.234.567.A-901.234", "123", "12345678901234567", "0001 2345 6789 0123"]:
            with self.subTest(value=value):
                self.raw["npwp"]["raw"] = value
                self.assertIn("INVALID_NPWP_STRUCTURE", self.codes("npwp"))

    def test_npwp_optional_absent_unless_explicitly_available_and_not_copied_from_id(self):
        self.raw["npwp"].update(raw=None, complete=None, available=None)
        report = self.validate()
        self.assertEqual(report["fields"]["npwp"]["status"], "NOT_PRESENT")
        self.assertIsNone(report["normalized"]["npwp"])
        self.raw["npwp"]["complete"] = False
        self.assertIn("NPWP_REGION_UNREADABLE", self.codes("npwp"))
        self.raw["npwp"]["available"] = True
        self.assertIn("REQUIRED", self.codes("npwp"))
        self.raw["npwp"].update(raw="012345678901234", complete=True, available=False)
        self.assertIn("NPWP_AVAILABILITY_CONFLICT", self.codes("npwp"))

    def test_usage_purpose_and_receipt_source_required_complete_free_text(self):
        for field in ["usage_purpose", "receipt_source"]:
            for value in [None, "@@@"]:
                self.raw = evidence(); self.raw[field]["raw"] = value
                self.assertEqual(self.validate()["fields"][field]["status"], "FAIL")
            self.raw = evidence(); self.raw[field]["complete"] = False
            self.assertIn("TEXT_INCOMPLETE_OR_UNREADABLE", self.codes(field))
            self.raw = evidence(); self.raw[field]["complete"] = None
            self.assertEqual(self.validate()["fields"][field]["status"], "REVIEW")

    def test_usage_business_day_rejects_weekend_future_and_public_holiday(self):
        for value, code in [("10-08-2025", "WEEKEND"), ("06-10-2026", "FUTURE_DATE"),
                            ("17-08-2025", "INDONESIAN_HOLIDAY_OR_JOINT_LEAVE")]:
            with self.subTest(value=value):
                self.raw["usage_date"] = value
                self.assertIn(code, self.codes("usage_date"))
        self.raw["usage_date"] = "07-08-2025"; self.policy["additional_closed_dates"] = ["2025-08-07"]
        self.assertIn("BANK_CLOSED_DATE", self.codes("usage_date"))

    def test_receipt_date_has_no_unsupplied_business_day_or_future_restriction(self):
        for value in ["10-08-2025", "07-10-2026"]:
            self.raw["receipt_date"] = value
            self.assertEqual(self.validate()["fields"]["receipt_date"]["status"], "PASS")
        self.raw["creation_date"] = "10-08-2025"
        self.assertEqual(self.validate()["fields"]["creation_date"]["status"], "PASS")
        self.raw["creation_date"] = "06-10-2026"
        self.assertIn("FUTURE_DATE", self.codes("creation_date"))

    def test_all_date_fields_reject_impossible_and_incomplete_dates(self):
        for field in ["usage_date", "receipt_date", "creation_date"]:
            for value in [None, "31/02/2025", "August 2025"]:
                self.raw = evidence(); self.raw[field] = value
                self.assertIn("INVALID_OR_MISSING_DATE", self.codes(field))
        self.raw = evidence(); self.raw["usage_date"] = "07-Aug-2025"
        self.assertEqual(self.validate()["normalized"]["usage_date"], "07-08-2025")

    def test_money_positive_decimal_indonesian_separators_and_large_precision(self):
        for field in ["usage_amount", "receipt_amount"]:
            for value, expected in [("1.500", Decimal("1500")), ("1.500,25", Decimal("1500.25")),
                                    ("0,01", Decimal("0.01")), ("999.999.999.999.999,99", Decimal("999999999999999.99"))]:
                with self.subTest(field=field, value=value):
                    self.raw[field]["amount_raw"] = value
                    self.assertEqual(self.validate()["fields"][field]["status"], "PASS")
                    self.assertEqual(self.validate()["normalized"][field]["amount"], expected)

    def test_money_rejects_zero_negative_us_format_symbols_and_scientific_notation(self):
        for field in ["usage_amount", "receipt_amount"]:
            for value in [None, "0", "-1,25", "1,500.25", "1.50", "1e6", "USD 150.000", "Rp 150.000", "NaN"]:
                self.raw = evidence(); self.raw[field]["amount_raw"] = value
                self.assertEqual(self.validate()["fields"][field]["status"], "FAIL")

    def test_money_currency_required_iso_and_ambiguous_symbol_review(self):
        for field in ["usage_amount", "receipt_amount"]:
            for value in [None, "ZZZ", "US", "123"]:
                self.raw = evidence(); self.raw[field]["currency_raw"] = value
                self.assertIn("INVALID_OR_MISSING_ISO_4217_CODE", self.codes(field))
            self.raw = evidence(); self.raw[field]["currency_raw"] = "$"
            self.assertIn("CURRENCY_AMBIGUOUS", self.codes(field))
            self.assertIsNone(self.validate()["normalized"][field]["currency"])
            self.raw = evidence(); self.raw[field]["currency_raw"] = "Euro"
            self.assertEqual(self.validate()["normalized"][field]["currency"], "EUR")

    def test_signatory_name_role_company_required_for_company(self):
        self.raw["signatory"]["role_raw"] = None
        self.assertIn("SIGNATORY_ROLE_REQUIRED", self.codes("signatory"))
        self.raw = evidence(); self.raw["signatory_company"]["raw"] = None
        self.assertIn("REQUIRED", self.codes("signatory_company"))

    def test_individual_can_omit_company_and_role_but_unknown_capacity_is_review(self):
        self.raw["customer_name"].update(raw="Rina Putri", subject_type="individual")
        self.raw["signatory"].update(raw=None, name_raw=None, role_raw=None, complete=None,
                                    is_company_representative=False, capacity_evidence="Individual self signing option selected.")
        self.raw["signatory_company"].update(raw=None, complete=None)
        report = self.validate()
        self.assertEqual(report["fields"]["signatory"]["status"], "NOT_APPLICABLE")
        self.assertEqual(report["fields"]["signatory_company"]["status"], "NOT_APPLICABLE")
        self.raw["signatory"]["capacity_evidence"] = None
        self.assertIn("SIGNATORY_CAPACITY_UNCERTAIN", self.codes("signatory"))

    def test_mandatory_handwritten_signature_and_stamp_denomination_cropping(self):
        for attribute in ["present", "handwritten", "complete"]:
            self.raw = evidence(); self.raw["signatory_signature"][attribute] = False
            self.assertEqual(self.validate()["fields"]["signatory_signature"]["status"], "FAIL")
        self.raw = evidence(); self.raw["stamp_duty"]["denomination_raw"] = "Rp6000"
        self.assertIn("INVALID_OR_MISSING_STAMP_DUTY_DENOMINATION", self.codes("stamp_duty"))
        self.raw = evidence(); self.raw["stamp_duty"]["complete"] = False
        self.assertIn("STAMP_DUTY_CROPPED_OR_UNREADABLE", self.codes("stamp_duty"))

    def test_meterai_authenticity_requires_job_matched_trusted_verification(self):
        self.context = {}
        self.assertIn("STAMP_DUTY_AUTHENTICITY_REQUIRES_EXTERNAL_VERIFICATION", self.codes("stamp_duty"))
        self.context = verified_context(job="ext-other-valas1")
        self.assertEqual(self.validate()["normalized"]["stamp_duty"]["authenticity_status"], "unverified")
        self.context = verified_context(job="ext-synthetic-valas1", status="rejected")
        self.assertIn("STAMP_DUTY_AUTHENTICITY_REJECTED", self.codes("stamp_duty"))

    def test_low_confidence_and_schema_mismatch_retain_review_fail_semantics(self):
        self.meta["field_metadata"]["document_metadata"]["usage_amount"]["confidence"] = .4
        self.assertIn("LOW_EXTRACTION_CONFIDENCE", self.codes("usage_amount"))
        self.raw["usage_amount"]["amount_raw"] = 150000
        with self.assertRaises(ValueError): self.validate()

    def test_offline_replay_exports_sixteen_headers_and_numeric_amounts_with_raw_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); replay = folder / "response.json"; output = folder / "out"
            replay.write_text(json.dumps({"id": "ext-synthetic-valas1", "status": "COMPLETED",
                                         "extract_result": evidence(), "extract_metadata": metadata()}))
            with patch.object(run, "LlamaCloud", side_effect=AssertionError("Unexpected network")):
                self.assertEqual(run.main(["--document-type", "valas_declaration_1", "--replay", str(replay),
                                           "--as-of", "2026-10-05", "--output", str(output)]), 0)
            with (output / "result.csv").open(encoding="utf-8-sig", newline="") as f:
                headers, row = list(csv.reader(f))
            self.assertEqual(headers, [label for _, label in COLUMNS]); self.assertEqual(len(row), 16)
            self.assertEqual(row[2], "0001234567890123"); self.assertEqual(row[3], "012345678901234")
            money = json.loads(row[6]); self.assertEqual(money["amount"], 150000.5); self.assertEqual(money["currency"], "USD")
            self.assertEqual(run.read(output / "raw.json")["usage_amount"]["amount_raw"], "150.000,50")
            self.assertEqual(run.read(output / "validation.json")["status"], "REVIEW")

    def test_cli_replay_context_is_bound_to_actual_extraction_job(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); replay = folder / "response.json"; policy = folder / "policy.json"; context = folder / "context.json"
            run.save(replay, {"id": "ext-synthetic-valas1", "status": "COMPLETED", "extract_result": evidence(), "extract_metadata": metadata()})
            run.save(policy, self.policy); run.save(context, self.context)
            self.assertEqual(run.main(["--document-type", "valas_declaration_1", "--replay", str(replay), "--policy", str(policy),
                                      "--validation-context", str(context), "--as-of", "2026-10-05", "--output", str(folder / "out")]), 0)
            self.assertEqual(run.read(folder / "out/validation.json")["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
