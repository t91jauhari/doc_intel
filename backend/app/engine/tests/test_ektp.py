"""Synthetic eKTP extraction observations and offline rule/export checks."""
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
from ektp.schema import SCHEMA, COLUMNS
from ektp.validation import validate

ROOT = Path(__file__).resolve().parents[1]


def evidence():
    def text(value): return {"raw": value, "complete": True}
    return {
        "nik": "0001234567890123", "name": text(" Rina Putri "), "birth_place": text(" Jakarta Selatan "),
        "birth_date": "1 Juni 1993", "gender": "perempuan", "blood_type": "ab", "address": text("Jl. Contoh 12, Blok A/3"),
        "rt": "4", "rw": "12", "village": text("Contoh Desa"), "district": text("Contoh Kecamatan"),
        "religion": "islam", "marital_status": "belum kawin", "occupation": text("Karyawan Swasta"),
        "citizenship": "wni", "valid_until": "Seumur Hidup",
        "issuance": {"raw": "Kota Adm. Jakarta Selatan, 7 Agustus 2025", "place_raw": " Kota Adm. Jakarta Selatan ",
                     "place_complete": True, "date_raw": "7 Agustus 2025"},
        "owner_signature": {"present": True, "non_text": True, "complete": True, "corrupted": False,
                            "evidence": "Non-text ink signature strokes visible in cardholder region."},
        "owner_photo": {"present": True, "face_visible": True, "face_cropped": False,
                        "evidence": "Holder portrait with entire face visible within the image boundary."},
        "stamp_verification": {"present": False, "text": None, "complete": None,
                               "evidence": "No distinct stamp observed after inspecting card."},
    }


def metadata():
    return {"field_metadata": {"document_metadata": {k: {"confidence": .99} for k, _ in COLUMNS}}}


def comparison_context(job="ext-synthetic-ektp", nik="0001234567890123", status="matched"):
    return {"signature_comparisons": [{"extract_job_id": job, "nik": nik, "status": status,
             "reference_id": "synthetic-reference-id", "comparison_reference": "synthetic-comparison-result",
             "verified_by": "synthetic-reviewer"}]}


class EKTPTests(unittest.TestCase):
    def setUp(self):
        self.raw = evidence()
        self.policy = run.read(ROOT / "ektp/policy.json")
        self.policy.update(stamp_rule_confirmed=True, stamp_required=False)
        self.context = comparison_context()
        self.meta = metadata()

    def validate(self):
        return validate(self.raw, self.meta, self.policy, date(2026, 10, 5),
                        validation_context=self.context, extract_job_id="ext-synthetic-ektp")

    def codes(self, field, report=None):
        return [i["code"] for i in (report or self.validate())["fields"][field]["issues"]]

    def test_exact_twenty_fields_order_and_normalization(self):
        report = self.validate()
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["document_type"], "ektp")
        self.assertEqual(len(COLUMNS), 20)
        self.assertEqual(list(SCHEMA["properties"]), [k for k, _ in COLUMNS])
        self.assertEqual(report["normalized"]["nik"], "0001234567890123")
        self.assertEqual(report["normalized"]["rt"], "004")
        self.assertEqual(report["normalized"]["rw"], "012")
        self.assertEqual(report["normalized"]["name"], "Rina Putri")
        self.assertEqual(report["normalized"]["valid_until"], "SEUMUR HIDUP")
        self.assertEqual(report["raw"]["rt"], "4")

    def test_nik_exact_digits_no_trimming_padding_or_ocr_character_repair(self):
        for value in [None, "123", "12345678901234567", "0001 234567890123", "0001.234567890123",
                      " 0001234567890123", "0001234567890123 ", "O001234567890123", "٠٠٠١٢٣٤٥٦٧٨٩٠١٢٣"]:
            with self.subTest(value=value):
                self.raw["nik"] = value
                report = self.validate()
                self.assertEqual(report["fields"]["nik"]["status"], "FAIL")
                self.assertEqual(report["normalized"]["nik"], value)

    def test_name_and_birthplace_alphabetic_only_symbols_digits_rejected(self):
        for field in ["name", "birth_place"]:
            for value in ["Rina 2", "Rina-Putri", "M. Rina", "@@", "123", None]:
                self.raw = evidence(); self.raw[field]["raw"] = value
                self.assertEqual(self.validate()["fields"][field]["status"], "FAIL")
            self.raw = evidence(); self.raw[field]["raw"] = "Rína   Putri"
            self.assertEqual(self.validate()["normalized"][field], "Rína Putri")

    def test_full_free_text_fields_preserve_punctuation_and_detect_truncation(self):
        for field in ["address", "village", "district", "occupation"]:
            self.raw = evidence(); self.raw[field]["raw"] = "Contoh 1, Blok A/3 (Timur)"
            self.assertEqual(self.validate()["fields"][field]["status"], "PASS")
            self.raw[field]["complete"] = False
            self.assertIn("TEXT_INCOMPLETE_OR_UNREADABLE", self.codes(field))
            self.raw[field]["complete"] = None
            self.assertEqual(self.validate()["fields"][field]["status"], "REVIEW")
            self.raw[field]["raw"] = None
            self.assertIn("REQUIRED", self.codes(field))

    def test_rt_rw_padding_preserves_three_digit_values_and_does_not_swap(self):
        for value, expected in [("4", "004"), ("12", "012"), ("001", "001"), ("999", "999"), ("0", "000")]:
            self.raw["rt"] = value
            self.assertEqual(self.validate()["normalized"]["rt"], expected)
        self.raw["rt"] = "1"; self.raw["rw"] = "5"
        report = self.validate()
        self.assertEqual((report["normalized"]["rt"], report["normalized"]["rw"]), ("001", "005"))
        self.assertTrue(any(x["method"] == "trim_and_left_pad_to_three_digits" for x in report["corrections"]))

    def test_rt_rw_reject_empty_overlong_letters_and_whole_pair(self):
        for field in ["rt", "rw"]:
            for value in [None, "1234", "1A", "001/005", "1.2", "1 2", "-1"]:
                self.raw = evidence(); self.raw[field] = value
                self.assertEqual(self.validate()["fields"][field]["status"], "FAIL")

    def test_gender_only_full_allowed_values_case_insensitive(self):
        for value, expected in [("LAKI-LAKI", "Laki-Laki"), ("perempuan", "Perempuan")]:
            self.raw["gender"] = value
            self.assertEqual(self.validate()["normalized"]["gender"], expected)
        for value in [None, "L", "Wanita", "Laki Laki", "Other"]:
            self.raw["gender"] = value
            self.assertIn("MISSING_ENUM" if value is None else "UNRECOGNIZED_ENUM", self.codes("gender"))

    def test_blood_type_hyphen_is_valid_unknown_but_blank_invalid(self):
        for value in ["a", "B", "ab", "O", "-"]:
            self.raw["blood_type"] = value
            self.assertEqual(self.validate()["fields"]["blood_type"]["status"], "PASS")
            self.assertEqual(self.validate()["normalized"]["blood_type"], value.upper())
        for value in [None, "", "?", "A+", "0"]:
            self.raw["blood_type"] = value
            self.assertEqual(self.validate()["fields"]["blood_type"]["status"], "FAIL" if value in (None, "") else "REVIEW")

    def test_religion_exact_case_insensitive_values_no_fuzzy_spelling_repair(self):
        for value in self.policy["religion_values"]:
            self.raw["religion"] = value.upper()
            self.assertEqual(self.validate()["normalized"]["religion"], value)
        for value, status, normalized in [(None, "FAIL", None), ("Isalm", "REVIEW", "Isalm"),
                                          ("Budha", "PASS", "Buddha"),
                                          ("KEPERCAYAAN TERHADAP TUHAN YME", "REVIEW", "KEPERCAYAAN TERHADAP TUHAN YME")]:
            self.raw["religion"] = value
            report = self.validate()
            self.assertEqual(report["fields"]["religion"]["status"], status)
            self.assertEqual(report["normalized"]["religion"], normalized)

    def test_marital_status_rejects_abbreviations_and_invalid_values(self):
        for value in self.policy["marital_status_values"]:
            self.raw["marital_status"] = value.upper()
            self.assertEqual(self.validate()["normalized"]["marital_status"], value)
        for value in [None, "BK", "Married", "Belum", "Cerai"]:
            self.raw["marital_status"] = value
            self.assertIn("MISSING_ENUM" if value is None else "UNRECOGNIZED_ENUM", self.codes("marital_status"))

    def test_citizenship_only_wni_wna(self):
        for value in ["wni", "wna"]:
            self.raw["citizenship"] = value
            self.assertEqual(self.validate()["normalized"]["citizenship"], value.upper())
        for value in [None, "Indonesia", "W.N.I", "IDN"]:
            self.raw["citizenship"] = value
            self.assertEqual(self.validate()["fields"]["citizenship"]["status"], "FAIL" if value is None else "REVIEW")

    def test_birthdate_multiformat_indonesian_english_and_nonfuture(self):
        for value in ["1/6/1993", "01-06-1993", "1993-06-01", "1 Juni 1993", "01-Jun-1993", "1 Juni 1993."]:
            self.raw["birth_date"] = value
            self.assertEqual(self.validate()["normalized"]["birth_date"], "01-06-1993")
        self.raw["birth_date"] = "06-10-2026"
        self.assertIn("FUTURE_DATE", self.codes("birth_date"))

    def test_lifetime_validity_and_explicit_supplied_nonfuture_expiry_rule(self):
        self.raw["valid_until"] = " seumur hidup "
        self.assertEqual(self.validate()["normalized"]["valid_until"], "SEUMUR HIDUP")
        self.raw["valid_until"] = "07-08-2025"
        self.assertEqual(self.validate()["fields"]["valid_until"]["status"], "PASS")
        self.raw["valid_until"] = "01-01-2027"
        self.assertIn("FUTURE_DATE", self.codes("valid_until"))
        self.raw["valid_until"] = "Lifetime"
        self.assertIn("INVALID_OR_MISSING_DATE", self.codes("valid_until"))

    def test_issuance_has_separate_place_and_date_and_allows_city_punctuation(self):
        report = self.validate()
        self.assertEqual(report["normalized"]["issuance"], {"place": "Kota Adm. Jakarta Selatan", "date": "07-08-2025"})
        self.assertEqual(report["normalized"]["birth_place"], "Jakarta Selatan")
        self.assertEqual(report["normalized"]["birth_date"], "01-06-1993")
        for value in [None, "123", "@@", "Jakarta 2"]:
            self.raw["issuance"]["place_raw"] = value
            self.assertEqual(self.validate()["fields"]["issuance"]["status"], "FAIL")
        self.raw = evidence(); self.raw["issuance"]["place_complete"] = False
        self.assertIn("ISSUANCE_PLACE_INCOMPLETE_OR_UNREADABLE", self.codes("issuance"))

    def test_all_dates_reject_missing_impossible_incomplete_and_future_issuance(self):
        for field in ["birth_date", "valid_until"]:
            for value in [None, "31-02-2025", "August 2025"]:
                self.raw = evidence(); self.raw[field] = value
                self.assertIn("INVALID_OR_MISSING_DATE", self.codes(field))
        for value in [None, "31-02-2025", "06-10-2026"]:
            self.raw = evidence(); self.raw["issuance"]["date_raw"] = value
            self.assertEqual(self.validate()["fields"]["issuance"]["status"], "FAIL")

    def test_owner_signature_missing_text_only_cropped_or_corrupted_fail(self):
        for attribute in ["present", "non_text", "complete"]:
            self.raw = evidence(); self.raw["owner_signature"][attribute] = False
            self.assertEqual(self.validate()["fields"]["owner_signature"]["status"], "FAIL")
        self.raw = evidence(); self.raw["owner_signature"]["corrupted"] = True
        self.assertIn("OWNER_SIGNATURE_CORRUPTED", self.codes("owner_signature"))

    def test_signature_unclear_observations_and_missing_local_evidence_review(self):
        for attribute in ["present", "non_text", "complete", "corrupted"]:
            self.raw = evidence(); self.raw["owner_signature"][attribute] = None
            self.assertEqual(self.validate()["fields"]["owner_signature"]["status"], "REVIEW")
        self.raw = evidence(); self.raw["owner_signature"]["evidence"] = None
        self.assertIn("SIGNATURE_VISUAL_EVIDENCE_MISSING", self.codes("owner_signature"))

    def test_visible_signature_without_reference_match_remains_review(self):
        self.context = {}
        self.assertIn("SIGNATURE_MATCH_REQUIRES_EXTERNAL_COMPARISON", self.codes("owner_signature"))
        self.assertEqual(self.validate()["normalized"]["owner_signature"]["comparison_status"], "unverified")
        self.context = comparison_context(status="unknown")
        self.assertEqual(self.validate()["fields"]["owner_signature"]["status"], "REVIEW")

    def test_external_signature_mismatch_fails_and_matching_does_not_override_bad_region(self):
        self.context = comparison_context(status="mismatched")
        self.assertIn("OWNER_SIGNATURE_REFERENCE_MISMATCH", self.codes("owner_signature"))
        self.context = comparison_context(); self.raw["owner_signature"]["present"] = False
        self.assertEqual(self.validate()["fields"]["owner_signature"]["status"], "FAIL")

    def test_signature_comparison_must_match_both_extraction_id_and_nik(self):
        self.context = comparison_context(job="ext-other")
        self.assertEqual(self.validate()["normalized"]["owner_signature"]["comparison_status"], "unverified")
        self.context = comparison_context(nik="9991234567890123")
        self.assertIn("SIGNATURE_COMPARISON_NIK_CONFLICT", self.codes("owner_signature"))
        self.assertEqual(self.validate()["fields"]["owner_signature"]["status"], "REVIEW")

    def test_duplicate_and_malformed_external_comparisons_do_not_pass(self):
        self.context["signature_comparisons"] *= 2
        self.assertIn("DUPLICATE_OR_CONFLICTING_SIGNATURE_COMPARISONS", self.codes("owner_signature"))
        self.context = {"signature_comparisons": [{"status": "matched"}]}
        with self.assertRaises(ValueError): self.validate()
        self.context = []
        with self.assertRaises(ValueError): self.validate()

    def test_photo_missing_face_not_visible_or_cropped_fail(self):
        for attribute in ["present", "face_visible"]:
            self.raw = evidence(); self.raw["owner_photo"][attribute] = False
            self.assertEqual(self.validate()["fields"]["owner_photo"]["status"], "FAIL")
        self.raw = evidence(); self.raw["owner_photo"]["face_cropped"] = True
        self.assertIn("OWNER_FACE_CROPPED", self.codes("owner_photo"))

    def test_photo_uncertainty_or_missing_evidence_requires_review(self):
        for attribute in ["present", "face_visible", "face_cropped"]:
            self.raw = evidence(); self.raw["owner_photo"][attribute] = None
            self.assertEqual(self.validate()["fields"]["owner_photo"]["status"], "REVIEW")
        self.raw = evidence(); self.raw["owner_photo"]["evidence"] = None
        self.assertIn("PHOTO_VISUAL_EVIDENCE_MISSING", self.codes("owner_photo"))

    def test_unknown_linked_stamp_rule_number_six_requires_review_without_guessing_presence(self):
        self.policy = run.read(ROOT / "ektp/policy.json")
        self.assertIn("STAMP_REQUIREMENT_NUMBER_6_NOT_CONFIGURED", self.codes("stamp_verification"))
        self.assertEqual(self.validate()["fields"]["stamp_verification"]["status"], "REVIEW")

    def test_configured_stamp_presence_legibility_text_and_optional_absence(self):
        self.policy.update(stamp_required=True, required_stamp_text_fragments=["CONTOH"])
        self.assertIn("STAMP_REQUIRED", self.codes("stamp_verification"))
        self.raw["stamp_verification"].update(present=True, text="Contoh", complete=True, evidence="Whole relevant stamp visible.")
        self.assertEqual(self.validate()["fields"]["stamp_verification"]["status"], "PASS")
        self.raw["stamp_verification"]["text"] = "OTHER"
        self.assertEqual(self.validate()["fields"]["stamp_verification"]["status"], "FAIL")
        self.raw["stamp_verification"].update(text="Contoh", complete=False)
        self.assertIn("STAMP_CROPPED_OR_UNREADABLE", self.codes("stamp_verification"))

    def test_confidence_missing_low_invalid_and_schema_types(self):
        self.meta = None
        self.assertIn("CONFIDENCE_UNAVAILABLE", self.codes("nik"))
        self.meta = metadata(); self.meta["field_metadata"]["document_metadata"]["nik"]["confidence"] = .1
        self.assertIn("LOW_EXTRACTION_CONFIDENCE", self.codes("nik"))
        self.meta["field_metadata"]["document_metadata"]["nik"]["confidence"] = 2
        self.assertIn("INVALID_EXTRACTION_CONFIDENCE", self.codes("nik"))
        self.raw["nik"] = 1234567890123456
        with self.assertRaises(ValueError): self.validate()

    def test_offline_cli_exports_twenty_columns_and_preserves_raw_zero_padding_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); replay = folder / "response.json"; out = folder / "out"
            run.save(replay, {"id": "ext-synthetic-ektp", "status": "COMPLETED", "extract_result": evidence(), "extract_metadata": metadata()})
            with patch.object(run, "LlamaCloud", side_effect=AssertionError("Unexpected network")):
                self.assertEqual(run.main(["--document-type", "ektp", "--replay", str(replay), "--as-of", "2026-10-05", "--output", str(out)]), 0)
            with (out / "result.csv").open(encoding="utf-8-sig", newline="") as f:
                headers, row = list(csv.reader(f))
            self.assertEqual(headers, [label for _, label in COLUMNS]); self.assertEqual(len(row), 20)
            self.assertEqual(row[0], "0001234567890123"); self.assertEqual(row[7], "004"); self.assertEqual(row[8], "012")
            self.assertEqual(json.loads(row[16])["date"], "07-08-2025")
            self.assertEqual(run.read(out / "raw.json")["rt"], "4")
            self.assertEqual(run.read(out / "validation.json")["status"], "REVIEW")

    def test_cli_replay_binds_comparison_to_actual_extraction_and_configured_stamp(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); replay = folder / "response.json"; policy = folder / "policy.json"; context = folder / "context.json"
            run.save(replay, {"id": "ext-synthetic-ektp", "status": "COMPLETED", "extract_result": evidence(), "extract_metadata": metadata()})
            run.save(policy, self.policy); run.save(context, self.context)
            self.assertEqual(run.main(["--document-type", "ektp", "--replay", str(replay), "--policy", str(policy),
                                      "--validation-context", str(context), "--as-of", "2026-10-05", "--output", str(folder / "out")]), 0)
            self.assertEqual(run.read(folder / "out/validation.json")["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
