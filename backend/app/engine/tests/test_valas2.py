"""Synthetic Valas 2 rule checks and offline CLI export tests; no live OCR claims."""
from copy import deepcopy
from datetime import date
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run
from profiles import get_profile
from valas2.schema import SCHEMA, COLUMNS
from valas2.validation import validate

ROOT = Path(__file__).resolve().parents[1]


def evidence():
    return {
        "customer_name": {"raw": " PT Contoh & Mitra. ", "complete": True, "subject_type": "company"},
        "customer_address": {"raw": " Jalan Contoh 12, Jakarta ", "complete": True},
        "currency": "usd", "creation_place": {"raw": " Jakarta ", "complete": True},
        "creation_date": "5 Oktober 2026",
        "signatory": {"raw": "Rina Putri, Direktur", "name_raw": " Rina Putri ", "role_raw": " Direktur ",
                      "complete": True, "is_company_representative": True,
                      "capacity_evidence": "Filled signer role Direktur and represented company PT Contoh & Mitra."},
        "signatory_company": {"raw": "PT Contoh & Mitra.", "complete": True},
        "stamp_duty": {"present": True, "denomination_raw": "Rp10 000", "complete": True,
                       "suspected_tampering": False, "evidence": "Whole fiscal stamp with readable Rp10 000 denomination."},
        "signatory_signature": {"present": True, "handwritten": True, "complete": True,
                                "evidence": "Distinct handwritten ink signature in signer region."},
        "stamp_verification": {"present": True, "text": "PT Contoh & Mitra.", "complete": True,
                               "evidence": "Whole round company stamp beside signature."},
    }


def metadata():
    return {"field_metadata": {"document_metadata": {k: {"confidence": .99} for k, _ in COLUMNS}}}


def verified_context(job="ext-synthetic-valas2", status="verified"):
    return {"stamp_duty_verifications": [{"extract_job_id": job, "status": status,
             "verification_reference": "synthetic-reviewed-reference", "verified_by": "synthetic-reviewer"}]}


class Valas2Tests(unittest.TestCase):
    def setUp(self):
        self.raw = evidence()
        self.policy = run.read(ROOT / "valas2/policy.json")
        self.policy.update(stamp_rule_confirmed=True, stamp_required=True,
                           required_stamp_text_fragments=["PT Contoh & Mitra."])
        self.meta = metadata()
        self.context = verified_context()

    def validate(self, **kwargs):
        return validate(self.raw, self.meta, self.policy, date(2026, 10, 5),
                        validation_context=self.context, extract_job_id="ext-synthetic-valas2", **kwargs)

    def codes(self, field, report=None):
        return [i["code"] for i in (report or self.validate())["fields"][field]["issues"]]

    def individual(self):
        self.raw["customer_name"].update(raw="Rina Putri", subject_type="individual")
        self.raw["signatory"].update(raw=None, name_raw=None, role_raw=None, complete=None,
                                    is_company_representative=False,
                                    capacity_evidence="Individual/self signing selection visibly filled.")
        self.raw["signatory_company"].update(raw=None, complete=None)

    def test_exact_ten_fields_order_currency_only_and_structural_corrections(self):
        report = self.validate()
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(list(SCHEMA["properties"]), [k for k, _ in COLUMNS])
        self.assertEqual(len(COLUMNS), 10)
        self.assertEqual(report["normalized"]["currency"], "USD")
        self.assertEqual(report["normalized"]["creation_date"], "05-10-2026")
        self.assertEqual(report["normalized"]["customer_name"], "PT Contoh & Mitra.")
        self.assertEqual(report["raw"]["customer_name"]["raw"], " PT Contoh & Mitra. ")
        self.assertNotIn("amount", report["normalized"])
        self.assertTrue(report["corrections"])

    def test_required_names_addresses_completeness_and_symbol_only(self):
        for field in ["customer_name", "customer_address"]:
            for value, code in [(None, "REQUIRED"), (" @@@ ", "SYMBOL_ONLY_TEXT")]:
                with self.subTest(field=field, value=value):
                    self.raw = evidence(); self.raw[field]["raw"] = value
                    self.assertIn(code, self.codes(field))
            self.raw = evidence(); self.raw[field]["complete"] = False
            self.assertIn("TEXT_INCOMPLETE_OR_UNREADABLE", self.codes(field))
        self.raw = evidence(); self.raw["customer_address"]["complete"] = None
        self.assertEqual(self.validate()["fields"]["customer_address"]["status"], "REVIEW")

    def test_creation_place_rejects_numeric_and_symbols(self):
        for value in ["12345", "@@", None]:
            with self.subTest(value=value):
                self.raw["creation_place"]["raw"] = value
                self.assertEqual(self.validate()["fields"]["creation_place"]["status"], "FAIL")

    def test_currency_code_names_symbols_and_amount_contamination(self):
        for value, expected in [("EUR", "EUR"), ("Euro", "EUR"), ("Dolar Amerika Serikat", "USD"), ("rupiah", "IDR")]:
            with self.subTest(value=value):
                self.raw["currency"] = value
                self.assertEqual(self.validate()["normalized"]["currency"], expected)
        for value in [None, "ZZZ", "USD 100.000,00", "10000", "-10"]:
            with self.subTest(value=value):
                self.raw["currency"] = value
                self.assertEqual(self.validate()["fields"]["currency"]["status"], "FAIL")
        for value in ["$", "¥", "Dollar"]:
            self.raw["currency"] = value
            report = self.validate()
            self.assertEqual(report["fields"]["currency"]["status"], "REVIEW")
            self.assertIsNone(report["normalized"]["currency"])

    def test_date_formats_mixed_language_and_weekends_allowed(self):
        for value, expected in [("1/6/1993", "01-06-1993"), ("01-06-1993", "01-06-1993"),
                                ("2025-08-10", "10-08-2025"), ("10-Agu-2025", "10-08-2025"),
                                ("10 Aug 2025", "10-08-2025"), ("5 Oktober 2026", "05-10-2026")]:
            with self.subTest(value=value):
                self.raw["creation_date"] = value
                report = self.validate()
                self.assertEqual(report["fields"]["creation_date"]["status"], "PASS")
                self.assertEqual(report["normalized"]["creation_date"], expected)

    def test_future_impossible_incomplete_and_missing_dates_fail(self):
        for value in ["06-10-2026", "31-02-2025", "2025-13-01", "August 2025", None]:
            with self.subTest(value=value):
                self.raw["creation_date"] = value
                self.assertEqual(self.validate()["fields"]["creation_date"]["status"], "FAIL")

    def test_representative_requires_name_role_and_company(self):
        for field in ["name_raw", "role_raw"]:
            self.raw = evidence(); self.raw["signatory"][field] = None
            self.assertEqual(self.validate()["fields"]["signatory"]["status"], "FAIL")
        self.raw = evidence(); self.raw["signatory_company"]["raw"] = None
        self.assertIn("REQUIRED", self.codes("signatory_company"))

    def test_clearly_individual_can_omit_signer_role_company(self):
        self.individual()
        report = self.validate()
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["fields"]["signatory"]["status"], "NOT_APPLICABLE")
        self.assertEqual(report["fields"]["signatory_company"]["status"], "NOT_APPLICABLE")
        self.raw["signatory"].update(raw="Rina Putri", name_raw="Rina Putri", complete=True)
        self.assertEqual(self.validate()["fields"]["signatory"]["status"], "PASS")

    def test_blank_role_never_proves_individual_capacity(self):
        self.individual()
        self.raw["signatory"]["capacity_evidence"] = None
        report = self.validate()
        self.assertEqual(report["fields"]["signatory"]["status"], "REVIEW")
        self.assertEqual(report["fields"]["signatory_company"]["status"], "REVIEW")
        self.raw["signatory"]["is_company_representative"] = None
        self.assertIn("SIGNATORY_CAPACITY_UNCERTAIN", self.codes("signatory"))

    def test_company_cannot_claim_optional_self_signing_capacity(self):
        self.individual(); self.raw["customer_name"]["subject_type"] = "company"
        report = self.validate()
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("COMPANY_CUSTOMER_WITH_SELF_SIGNING_INDIVIDUAL_CAPACITY", self.codes("signatory", report))
        self.assertIn("REQUIRED", self.codes("signatory_company", report))

    def test_signer_rejects_numeric_names_roles_and_truncation(self):
        for key in ["name_raw", "role_raw"]:
            self.raw = evidence(); self.raw["signatory"][key] = "123"
            self.assertEqual(self.validate()["fields"]["signatory"]["status"], "FAIL")
        self.raw = evidence(); self.raw["signatory"]["complete"] = False
        self.assertIn("SIGNATORY_TEXT_INCOMPLETE", self.codes("signatory"))

    def test_role_component_without_visible_raw_support_requires_review(self):
        self.raw["signatory"]["raw"] = "Rina Putri"
        self.assertIn("SIGNATORY_ROLE_NOT_SUPPORTED_BY_RAW_TEXT", self.codes("signatory"))
        self.assertEqual(self.validate()["fields"]["signatory"]["status"], "REVIEW")

    def test_meterai_denomination_variants_and_wrong_or_missing_denomination(self):
        for value in ["Rp10 000", "Rp10.000", "10000", "Rp 10000", "SEPULUH RIBU RUPIAH"]:
            self.raw["stamp_duty"]["denomination_raw"] = value
            self.assertEqual(self.validate()["fields"]["stamp_duty"]["status"], "PASS")
        for value in ["Rp6000", "Rp0", "Rp-10000", None, "printed meterai Rp10000"]:
            self.raw["stamp_duty"]["denomination_raw"] = value
            self.assertIn("INVALID_OR_MISSING_STAMP_DUTY_DENOMINATION", self.codes("stamp_duty"))

    def test_blank_and_cropped_meterai_fail_even_with_verified_record(self):
        for key, code in [("present", "STAMP_DUTY_REQUIRED"), ("complete", "STAMP_DUTY_CROPPED_OR_UNREADABLE")]:
            self.raw = evidence(); self.raw["stamp_duty"][key] = False
            self.assertIn(code, self.codes("stamp_duty"))
            self.assertEqual(self.validate()["fields"]["stamp_duty"]["status"], "FAIL")

    def test_visible_meterai_never_proves_authenticity_without_matched_record(self):
        self.context = {}
        self.assertIn("STAMP_DUTY_AUTHENTICITY_REQUIRES_EXTERNAL_VERIFICATION", self.codes("stamp_duty"))
        self.context = verified_context(job="ext-other-document")
        self.assertEqual(self.validate()["normalized"]["stamp_duty"]["authenticity_status"], "unverified")
        self.assertEqual(self.validate()["fields"]["stamp_duty"]["status"], "REVIEW")

    def test_rejected_unknown_duplicate_and_malformed_verification_records(self):
        self.context = verified_context(status="rejected")
        self.assertIn("STAMP_DUTY_AUTHENTICITY_REJECTED", self.codes("stamp_duty"))
        self.context = verified_context(status="unknown")
        self.assertEqual(self.validate()["fields"]["stamp_duty"]["status"], "REVIEW")
        self.context = verified_context(); self.context["stamp_duty_verifications"] *= 2
        self.assertIn("CONFLICTING_OR_DUPLICATE_STAMP_DUTY_VERIFICATIONS", self.codes("stamp_duty"))
        self.context = {"stamp_duty_verifications": [{"status": "verified"}]}
        with self.assertRaises(ValueError): self.validate()

    def test_visible_tampering_and_missing_visual_evidence_require_review(self):
        self.raw["stamp_duty"]["suspected_tampering"] = True
        self.assertIn("STAMP_DUTY_SUSPECTED_TAMPERING", self.codes("stamp_duty"))
        self.raw["stamp_duty"]["evidence"] = None
        self.assertIn("STAMP_DUTY_VISUAL_EVIDENCE_MISSING", self.codes("stamp_duty"))

    def test_handwritten_signature_mandatory_and_typed_or_cropped_fail(self):
        for key in ["present", "handwritten", "complete"]:
            self.raw = evidence(); self.raw["signatory_signature"][key] = False
            self.assertEqual(self.validate()["fields"]["signatory_signature"]["status"], "FAIL")
        self.raw = evidence(); self.raw["signatory_signature"]["handwritten"] = None
        self.assertEqual(self.validate()["fields"]["signatory_signature"]["status"], "REVIEW")
        self.raw = evidence(); self.raw["signatory_signature"]["evidence"] = None
        self.assertEqual(self.validate()["fields"]["signatory_signature"]["status"], "REVIEW")

    def test_unconfigured_separate_stamp_criterion_requires_review(self):
        self.policy = run.read(ROOT / "valas2/policy.json")
        self.assertIn("STAMP_VERIFICATION_RULE_NOT_CONFIGURED", self.codes("stamp_verification"))
        self.raw["stamp_verification"]["present"] = False
        self.assertEqual(self.validate()["fields"]["stamp_verification"]["status"], "REVIEW")

    def test_configured_stamp_presence_text_completeness_and_optional_absence(self):
        self.raw["stamp_verification"]["text"] = "Wrong company"
        self.assertEqual(self.validate()["fields"]["stamp_verification"]["status"], "FAIL")
        self.raw = evidence(); self.raw["stamp_verification"]["complete"] = False
        self.assertIn("STAMP_CROPPED_OR_UNREADABLE", self.codes("stamp_verification"))
        self.raw = evidence(); self.raw["stamp_verification"]["present"] = False
        self.assertIn("STAMP_REQUIRED", self.codes("stamp_verification"))
        self.policy.update(stamp_required=False, required_stamp_text_fragments=[])
        self.assertEqual(self.validate()["fields"]["stamp_verification"]["status"], "NOT_APPLICABLE")

    def test_confidence_missing_low_invalid_and_schema_type_mismatch(self):
        self.meta = None
        self.assertIn("CONFIDENCE_UNAVAILABLE", self.codes("currency"))
        self.meta = metadata(); self.meta["field_metadata"]["document_metadata"]["currency"]["confidence"] = .2
        self.assertIn("LOW_EXTRACTION_CONFIDENCE", self.codes("currency"))
        self.meta["field_metadata"]["document_metadata"]["currency"]["confidence"] = 2
        self.assertIn("INVALID_EXTRACTION_CONFIDENCE", self.codes("currency"))
        self.raw["currency"] = 10000
        with self.assertRaises(ValueError): self.validate()

    def test_default_policy_replay_exports_ten_columns_with_review_and_no_network(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); replay = folder / "response.json"; output = folder / "out"
            replay.write_text(json.dumps({"id": "ext-synthetic-valas2", "status": "COMPLETED",
                                         "extract_result": evidence(), "extract_metadata": metadata()}))
            with patch.object(run, "LlamaCloud", side_effect=AssertionError("Unexpected network")):
                self.assertEqual(run.main(["--document-type", "valas_declaration_2", "--replay", str(replay),
                                           "--as-of", "2026-10-05", "--output", str(output)]), 0)
            with (output / "result.csv").open(encoding="utf-8-sig", newline="") as f:
                headers, row = list(csv.reader(f))
            self.assertEqual(headers, [label for _, label in COLUMNS]); self.assertEqual(len(row), 10)
            self.assertEqual(row[2], "USD")
            report = run.read(output / "validation.json")
            self.assertEqual(report["status"], "REVIEW")
            self.assertEqual(report["document_type"], "valas_declaration_2")

    def test_cli_replay_verification_is_bound_to_actual_extraction_id(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); replay = folder / "response.json"; policy = folder / "policy.json"; context = folder / "context.json"
            replay.write_text(json.dumps({"id": "ext-synthetic-valas2", "status": "COMPLETED",
                                         "extract_result": evidence(), "extract_metadata": metadata()}))
            run.save(policy, self.policy); run.save(context, self.context)
            code = run.main(["--document-type", "valas_declaration_2", "--replay", str(replay), "--policy", str(policy),
                             "--validation-context", str(context), "--as-of", "2026-10-05", "--output", str(folder / "out")])
            self.assertEqual(code, 0)
            self.assertEqual(run.read(folder / "out/validation.json")["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
