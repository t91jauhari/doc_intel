"""RIPLAY schema, page completeness, date ordering and evidence-bound checks."""

import csv
from copy import deepcopy
from datetime import date
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run
from riplay.schema import COLUMNS, SCHEMA
from riplay.validation import validate
from batch import discover, document_arguments, checkpoint, META_COLUMNS

ROOT = Path(__file__).resolve().parents[1]


def evidence():
    text = lambda s: {"raw": s, "complete": True}
    signature = lambda: {
        "present": True,
        "non_text": True,
        "complete": True,
        "corrupted": False,
        "page_number": 4,
        "evidence": "Visible handwritten strokes in labelled signer block on page four.",
    }
    stamp = lambda: {
        "present": False,
        "text": None,
        "complete": None,
        "at_signer_region": None,
        "page_number": None,
        "evidence": "Inspected labelled signer region; no stamp.",
    }
    return {
        "document_place": text(" Jakarta "),
        "document_date": "25 Agustus 2025",
        "bank_officer_name": text("Tari O’Neil."),
        "bank_officer_signature": signature(),
        "customer_name": text(" Rina Putri "),
        "customer_signature": signature(),
        "printed_date": "25/08/2025",
        "page_initials": {
            "page_count": 4,
            "pages": [
                {
                    "page_number": n,
                    "footer_present": True,
                    "non_text": True,
                    "complete": True,
                    "main_signature_present": n == 4,
                    "evidence": f"Visible handwritten customer initials in bottom-right margin of physical page {n}.",
                }
                for n in range(1, 5)
            ],
        },
        "customer_stamp": stamp(),
        "cs_stamp": stamp(),
    }


def metadata():
    return {
        "field_metadata": {
            "document_metadata": {k: {"confidence": 0.99} for k, _ in COLUMNS}
        }
    }


def comparison_context():
    return {
        "ektp_identity": {
            "name": "Rina Putri",
            "reference_id": "ektp-synthetic",
            "verified_by": "test-reviewer",
        },
        "signature_comparisons": [
            {
                "field": key,
                "signer_name": "Tari O’Neil."
                if key == "bank_officer_signature"
                else "Rina Putri",
                "extract_job_id": "ext-synthetic-riplay",
                "status": "matched",
                "reference_id": "synthetic-reference",
                "verified_by": "test-reviewer",
            }
            for key in [
                "bank_officer_signature",
                "customer_signature",
                *[f"page_initials.{n}" for n in range(1, 5)],
            ]
        ],
    }


class RiplayTests(unittest.TestCase):
    def setUp(self):
        self.raw, self.context = evidence(), comparison_context()
        self.policy = run.read(ROOT / "riplay/policy.json")
        for key in ["customer_stamp", "cs_stamp"]:
            self.policy[key].update(rule_confirmed=True, required=False)

    def report(self):
        return validate(
            self.raw,
            metadata(),
            self.policy,
            date(2026, 10, 6),
            validation_context=self.context,
            extract_job_id="ext-synthetic-riplay",
        )

    def codes(self, field):
        return [i["code"] for i in self.report()["fields"][field]["issues"]]

    def test_ten_columns_and_normalization(self):
        self.assertEqual(len(COLUMNS), 10)
        self.assertEqual(len(SCHEMA["properties"]), 10)
        report = self.report()
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["normalized"]["document_place"], "Jakarta")
        self.assertEqual(report["normalized"]["document_date"], "25-08-2025")
        self.assertEqual(report["raw"]["customer_name"]["raw"], " Rina Putri ")

    def test_impossible_future_and_sample_date_order(self):
        self.raw["document_date"] = "31/02/2025"
        self.assertIn("INVALID_OR_MISSING_DATE", self.codes("document_date"))
        self.raw["document_date"] = "25/08/2025"
        self.raw["printed_date"] = "31 Mei 2023"
        self.assertIn("PRINT_DATE_BEFORE_DOCUMENT_DATE", self.codes("printed_date"))
        self.raw["printed_date"] = "7/10/2026"
        self.assertIn("FUTURE_DATE", self.codes("printed_date"))

    def test_page_four_footer_is_not_required(self):
        self.raw["page_initials"]["pages"][3].update(footer_present=False, non_text=None, complete=None)
        self.assertEqual(self.report()["fields"]["page_initials"]["status"], "PASS")
        self.raw["page_initials"]["pages"][1]["footer_present"] = False
        self.assertIn("PAGE_2_BOTTOM_RIGHT_INITIAL_REQUIRED", self.codes("page_initials"))

    def test_missing_duplicate_or_uninspected_pages(self):
        self.raw["page_initials"]["pages"].pop()
        self.assertIn(
            "MISSING_DUPLICATE_OR_INVALID_PAGE_RECORDS", self.codes("page_initials")
        )
        self.raw = evidence()
        self.raw["page_initials"]["pages"][3]["page_number"] = 3
        self.assertIn(
            "MISSING_DUPLICATE_OR_INVALID_PAGE_RECORDS", self.codes("page_initials")
        )
        self.raw["page_initials"]["page_count"] = 3
        self.assertIn("EXPECTED_PAGE_COUNT_MISMATCH", self.codes("page_initials"))

    def test_names_allow_dots_apostrophes_but_not_digits(self):
        self.raw["bank_officer_name"]["raw"] = "Tari 123"
        self.assertIn(
            "NAME_LETTERS_SPACES_DOT_APOSTROPHE_ONLY", self.codes("bank_officer_name")
        )
        self.raw["customer_name"]["raw"] = "@@@"
        self.assertIn("NUMERIC_OR_SYMBOL_ONLY_TEXT", self.codes("customer_name"))

    def test_signature_typed_corrupt_or_mismatched(self):
        self.raw["customer_signature"].update(non_text=False, corrupted=True)
        self.assertIn(
            "HANDWRITTEN_SIGNATURE_REQUIRED", self.codes("customer_signature")
        )
        self.assertIn("SIGNATURE_REGION_CORRUPTED", self.codes("customer_signature"))
        self.context["signature_comparisons"][1]["status"] = "mismatched"
        self.assertIn(
            "SIGNATURE_REFERENCE_MISMATCH:customer_signature",
            self.codes("customer_signature"),
        )

    def test_comparison_must_bind_to_job_and_name(self):
        self.context["signature_comparisons"][1]["extract_job_id"] = "other-job"
        self.assertIn(
            "SIGNATURE_REFERENCE_COMPARISON_REQUIRED:customer_signature",
            self.codes("customer_signature"),
        )
        self.context["signature_comparisons"][0]["signer_name"] = "Different Officer"
        self.assertIn(
            "SIGNATURE_REFERENCE_COMPARISON_REQUIRED:bank_officer_signature",
            self.codes("bank_officer_signature"),
        )

    def test_identity_requires_one_trusted_reference(self):
        self.context.pop("ektp_identity")
        self.assertIn("EKTP_IDENTITY_REFERENCE_REQUIRED", self.codes("customer_name"))
        self.context["ektp_identity"] = {
            "name": "Other Name",
            "reference_id": "ektp",
            "verified_by": "test",
        }
        self.assertIn("EKTP_NAME_MISMATCH", self.codes("customer_name"))
        self.context = {"defer_identity_to_case": True}
        self.assertEqual(
            self.report()["pending_case_checks"], ["riplay.customer_name_vs_ektp.name"]
        )

    def test_distinct_stamp_rules_and_wrong_signer_placement(self):
        self.policy["customer_stamp"].update(rule_confirmed=False, required=None)
        self.assertIn(
            "STAMP_REQUIREMENT_18_NOT_CONFIGURED", self.codes("customer_stamp")
        )
        self.policy["cs_stamp"].update(rule_confirmed=True, required=True)
        self.raw["cs_stamp"].update(
            present=True,
            complete=True,
            at_signer_region=False,
            page_number=4,
            text="CS",
        )
        self.assertIn("STAMP_AT_SIGNER_REGION_INVALID", self.codes("cs_stamp"))
        self.assertNotIn("STAMP_REQUIREMENT_18_NOT_CONFIGURED", self.codes("cs_stamp"))

    def test_low_confidence_cannot_erase_fail(self):
        self.raw["customer_name"]["raw"] = "123"
        meta = metadata()
        meta["field_metadata"]["document_metadata"]["customer_name"]["confidence"] = 0.1
        report = validate(
            self.raw,
            meta,
            self.policy,
            date(2026, 10, 6),
            validation_context=self.context,
            extract_job_id="ext-synthetic-riplay",
        )
        self.assertEqual(report["fields"]["customer_name"]["status"], "FAIL")

    def test_replay_exports_ten_cells(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            response = tmp / "response.json"
            run.save(
                response,
                {
                    "id": "ext-synthetic-riplay",
                    "status": "COMPLETED",
                    "extract_result": self.raw,
                    "extract_metadata": metadata(),
                },
            )
            self.assertEqual(
                run.main(
                    [
                        "--document-type",
                        "riplay",
                        "--replay",
                        str(response),
                        "--output",
                        str(tmp / "output"),
                    ]
                ),
                0,
            )
            with (tmp / "output/result.csv").open(
                encoding="utf-8-sig", newline=""
            ) as f:
                rows = list(csv.reader(f))
            self.assertEqual(len(rows[0]), 10)
            self.assertEqual(len(rows[1]), 10)

    def test_batch_suffix_and_separate_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "customer_RIPLAY.PDF").write_bytes(b"%PDF-test")
            selected, ignored = discover(folder)
            self.assertEqual(selected[0][1], "riplay")
            row = {k: "" for k in META_COLUMNS}
            row.update(
                document_type="riplay",
                source_file="customer_RIPLAY.PDF",
                processing_status="COMPLETED",
                validation_status="REVIEW",
            )
            row.update({"riplay." + key: "value" for key, _ in COLUMNS})
            checkpoint(folder, [row], [])
            self.assertTrue((folder / "riplay_result.csv").exists())
            self.assertFalse((folder / "combined_result.csv").exists())


if __name__ == "__main__":
    unittest.main()
