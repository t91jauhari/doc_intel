"""Synthetic LLD evidence; not extracted values or ground truth for the uploaded scan."""
import csv
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run
from lld.schema import SCHEMA, COLUMNS
from lld.validation import validate
from profiles import get_profile


def empty(schema):
    if schema["type"] == "object":
        return {k: empty(v) for k, v in schema["properties"].items()}
    return None


def selection(label, code=None, other_labels=()):
    choices = [(label, code)] if label else []
    choices.extend((x, None) for x in other_labels)
    return {"selected": [label] if label else [], "selected_codes": [code] if code else [], "options_complete": True,
            "options": [{"label": x, "code": c, "state": "selected" if x == label else "unselected",
                         "local_mark_present": x == label, "tail_overlap_only": False,
                         "mark_type": "tick" if x == label else "none",
                         "evidence": "local tick body inside box" if x == label else "empty box, no local mark"} for x, c in choices]}


def evidence():
    raw = empty(SCHEMA)
    raw.update(transaction_date="2025 08 05", declaration_date="05/08/25", transaction_id="000001TX", account_type="01",
               beneficiary_postal_code="04567", payer_postal_code="00001", beneficiary_phone="+1 (555) 123-4567", payer_phone=None,
               beneficiary_country_code="USA", payer_country_code="ID", beneficiary_identification_number="0000123456789012",
               payer_identification_number="0100123456789012", depository_correspondent_bank_country_code="US",
               purpose="X012", transaction_code="S001")
    for party in ["beneficiary", "payer"]:
        for field in ["name", "address"]:
            raw[party + "_" + field] = {"raw": f"{party.title()} Test {field.title()}", "complete": True}
        raw[party + "_identification_type"] = selection("KTP", "B", ["NPWP", "SIM", "Paspor"])
        raw[party + "_bank"] = selection(None, other_labels=["Bank Pelapor", "KC/KP di LN", "Bank Lainnya", "Otoritas Moneter"])
        raw[party + "_international_organization"] = selection(None, other_labels=["Bank", "Non Bank"])
    raw["beneficiary_status"] = selection("Bukan Penduduk", other_labels=["Penduduk"])
    raw["payer_status"] = selection("Penduduk", other_labels=["Bukan Penduduk"])
    raw["beneficiary_category"] = selection("Perusahaan", "E0", ["Perorangan", "Pemerintah", "Bank Pelapor", "Non Bank"])
    raw["payer_category"] = selection("Perorangan", "A0", ["Perusahaan", "Pemerintah", "Bank Pelapor", "Non Bank"])
    raw["beneficiary_identity_relation"] = selection("Penerima dana ≠ Pembayar", other_labels=["Penerima dana = Pembayar"])
    raw["financial_relationship"] = selection("Non afiliasi", "N", ["Pemegang Saham", "Terafiliasi", "Group"])
    raw["transaction_value"] = {"currency_raw": "USD", "amount_raw": "150 000", "segmented_cells": True}
    raw["details"] = {"raw": None, "complete": None}
    raw["customer_signature"] = {"present": True, "handwritten": True}
    raw["bank_officer_signature"] = {"present": True, "handwritten": True}
    raw["bank_stamp"] = {"present": True, "text": "TEST BANK", "complete": True}
    return raw


class LLDTests(unittest.TestCase):
    def setUp(self):
        self.raw = evidence()
        self.policy = json.loads((run.ROOT / "lld/policy.json").read_text())
        # Synthetic master data for tests only, not an official bank master list.
        self.policy.update(account_type_master=["01", "02"], purpose_master={"X012": "Synthetic purpose"},
                           transaction_code_master=["S001"], template_category_master_confirmed=True, stamp_rule_confirmed=True)
        self.context = {"transaction_id_history_complete": True, "transaction_ids": [], "identity_history_complete": True, "identity_records": []}
        self.metadata = {"field_metadata": {"document_metadata": {k: {"confidence": .99} for k, _ in COLUMNS}}}

    def report(self):
        return validate(self.raw, self.metadata, self.policy, date(2026, 10, 5), validation_context=self.context)

    def test_valid_with_test_masters_and_complete_history(self):
        result = self.report()
        self.assertEqual(result["status"], "PASS", result["fields"])
        self.assertEqual(result["normalized"]["transaction_value"], {"currency": "USD", "amount": Decimal("150000")})
        self.assertEqual(result["raw"]["transaction_value"]["amount_raw"], "150 000")
        self.assertEqual(result["normalized"]["beneficiary_country_code"], "US")
        self.assertEqual(result["normalized"]["beneficiary_bank"], None)
        self.assertEqual(result["fields"]["beneficiary_bank"]["status"], "NOT_APPLICABLE")
        self.assertEqual(result["normalized"]["payer_identification_number"], "0100123456789012")

    def test_exact_36_columns_and_retained_currency(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            run.export(output, self.report())
            with (output / "result.csv").open(encoding="utf-8-sig", newline="") as f:
                header, row = list(csv.reader(f))
            self.assertEqual(len(header), 36)
            self.assertEqual(header.count("Sandi Negara"), 2)
            self.assertEqual(header.count("Bank"), 2)
            self.assertNotIn("Value Transaksi", header)
            self.assertEqual(row[28], "USD 150000")
            self.assertEqual(row[14], "0000123456789012")
            self.assertEqual(row[27], "0100123456789012")

    def test_unknown_masters_and_history_do_not_pass(self):
        self.policy.update(account_type_master=None, purpose_master=None, transaction_code_master=None)
        self.context = {}
        result = self.report()
        self.assertEqual(result["status"], "REVIEW")
        for key in ["account_type", "purpose", "transaction_code", "transaction_id", "payer_identification_number"]:
            self.assertEqual(result["fields"][key]["status"], "REVIEW")

    def test_known_master_rejects_unlisted_account_code(self):
        self.raw["account_type"] = "03"
        self.assertEqual(self.report()["fields"]["account_type"]["status"], "FAIL")

    def test_printed_bilingual_labels_retain_code_mapping(self):
        self.raw["payer_category"] = selection("d. Lembaga Keuangan non Bank/ Non Bank Financial Institutions", "D0", ["Perorangan / Individual"])
        self.raw["payer_identification_type"] = selection("b. Kartu Tanda Penduduk (KTP)", "B", ["NPWP"])
        result = self.report()
        self.assertEqual(result["normalized"]["payer_category"], "Lembaga Keuangan Non Bank")
        self.assertEqual(result["normalized"]["payer_identification_type"], "KTP")
        self.assertEqual(result["fields"]["payer_category"]["status"], "PASS")

    def test_country_postal_phone_constraints(self):
        self.raw.update(beneficiary_country_code="XYZ", payer_postal_code="123456", beneficiary_phone="CALL 123")
        result = self.report()
        for key in ["beneficiary_country_code", "payer_postal_code", "beneficiary_phone"]:
            self.assertEqual(result["fields"][key]["status"], "FAIL")

    def test_no_blank_country_inference_from_address(self):
        self.raw["beneficiary_country_code"] = None
        self.raw["beneficiary_address"]["raw"] = "Hong Kong test address"
        result = self.report()
        self.assertIsNone(result["normalized"]["beneficiary_country_code"])
        self.assertEqual(result["fields"]["beneficiary_country_code"]["status"], "FAIL")

    def test_bank_parent_and_subtype_are_contextual(self):
        self.raw["beneficiary_category"] = selection("Bank Pelapor", "C1", ["Perusahaan", "Perorangan"])
        self.raw["beneficiary_bank"] = selection("Bank Pelapor", "C1", ["KC/KP di LN", "Bank Lainnya", "Otoritas Moneter"])
        result = self.report()
        self.assertEqual(result["normalized"]["beneficiary_category"], "Bank")
        self.assertEqual(result["normalized"]["beneficiary_bank"], "Bank Pelapor")
        self.assertEqual(result["fields"]["beneficiary_international_organization"]["status"], "NOT_APPLICABLE")

    def test_international_bank_is_not_parent_bank(self):
        self.raw["beneficiary_category"] = selection("Bank", "F1", ["Perusahaan", "Perorangan"])
        self.raw["beneficiary_international_organization"] = selection("Bank", "F1", ["Non Bank"])
        result = self.report()
        self.assertEqual(result["normalized"]["beneficiary_category"], "Lembaga/Organisasi Internasional")
        self.assertEqual(result["normalized"]["beneficiary_international_organization"], "Bank")
        self.assertEqual(result["fields"]["beneficiary_bank"]["status"], "NOT_APPLICABLE")

    def test_same_party_selection_allows_document_skip(self):
        self.raw["beneficiary_identity_relation"] = selection("Penerima dana = Pembayar", other_labels=["Penerima dana ≠ Pembayar"])
        for key in list(self.raw):
            if key.startswith("payer_") or key in {"financial_relationship", "depository_correspondent_bank_country_code", "beneficiary_identification_type", "beneficiary_identification_number"}:
                self.raw[key] = empty(SCHEMA["properties"][key])
        result = self.report()
        self.assertEqual(result["normalized"]["beneficiary_identity_relation"], "Penerima dana = Pembayar")
        self.assertEqual(result["fields"]["payer_name"]["status"], "NOT_APPLICABLE")
        self.assertEqual(result["fields"]["beneficiary_identification_number"]["status"], "NOT_APPLICABLE")
        self.assertEqual(result["status"], "PASS")

    def test_relation_reconciliation_preserves_equal_and_not_equal(self):
        self.raw["beneficiary_identity_relation"]["selected"] = ["Penerima dana = Pembayar"]
        result = self.report()
        self.assertEqual(result["normalized"]["beneficiary_identity_relation"], "Penerima dana ≠ Pembayar")
        self.assertEqual(result["raw"]["beneficiary_identity_relation"]["selected"], ["Penerima dana = Pembayar"])
        self.assertEqual(result["fields"]["beneficiary_identity_relation"]["status"], "REVIEW")
        self.assertEqual(result["fields"]["payer_name"]["status"], "PASS")

    def test_local_mark_cannot_be_hidden_by_empty_raw_selection(self):
        self.raw["beneficiary_bank"] = selection("Bank Pelapor", "C1", ["Bank Lainnya"])
        self.raw["beneficiary_bank"]["selected"] = []
        result = self.report()
        self.assertEqual(result["normalized"]["beneficiary_bank"], "Bank Pelapor")
        self.assertEqual(result["fields"]["beneficiary_bank"]["status"], "REVIEW")
        self.assertIn("SUBTYPE_CONFLICTS_WITH_PARENT_CATEGORY", [x["code"] for x in result["fields"]["beneficiary_bank"]["issues"]])

    def test_optional_bank_does_not_hide_incomplete_evidence(self):
        self.raw["beneficiary_category"] = selection("Bank Pelapor", "C1", ["Perusahaan"])
        self.raw["beneficiary_bank"]["options_complete"] = False
        result = self.report()
        self.assertEqual(result["fields"]["beneficiary_bank"]["status"], "REVIEW")

    def test_duplicate_ids_checked_in_correct_scope(self):
        self.context["transaction_ids"] = ["000001TX"]
        self.context["identity_records"] = [{"transaction_id": "000001TX", "role": "payer", "value": "0100123456789012"}]
        result = self.report()
        self.assertEqual(result["fields"]["transaction_id"]["status"], "FAIL")
        self.assertEqual(result["fields"]["payer_identification_number"]["status"], "FAIL")

    def test_same_customer_identifier_in_another_transaction_is_allowed(self):
        self.context["identity_records"] = [{"transaction_id": "OTHER", "role": "payer", "value": "0100123456789012"}]
        self.assertEqual(self.report()["fields"]["payer_identification_number"]["status"], "PASS")

    def test_segmented_amount_never_invents_digits(self):
        self.raw["transaction_value"]["amount_raw"] = "15? 000"
        result = self.report()
        self.assertIsNone(result["normalized"]["transaction_value"]["amount"])
        self.assertEqual(result["fields"]["transaction_value"]["status"], "FAIL")

    def test_dates_have_separate_business_rules(self):
        self.raw["transaction_date"] = "04/10/2026"  # Sunday
        self.raw["declaration_date"] = "04/10/2026"
        result = self.report()
        self.assertEqual(result["fields"]["transaction_date"]["status"], "FAIL")
        self.assertEqual(result["fields"]["declaration_date"]["status"], "PASS")

    def test_stamp_alone_is_not_an_officer_signature(self):
        self.raw["bank_officer_signature"] = {"present": False, "handwritten": False}
        self.assertEqual(self.report()["fields"]["bank_officer_signature"]["status"], "FAIL")

    def test_checked_label_code_conflict_is_rejected(self):
        self.raw["payer_category"]["selected_codes"] = ["E0"]
        self.assertEqual(self.report()["fields"]["payer_category"]["status"], "FAIL")

    def test_cli_lld_replay_uses_lld_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            replay = root / "extract.json"
            replay.write_text(json.dumps({"status": "COMPLETED", "extract_result": self.raw, "extract_metadata": self.metadata}))
            out = root / "output"
            self.assertEqual(run.main(["--document-type", "lld", "--replay", str(replay), "--output", str(out), "--as-of", "2026-10-05"]), 0)
            self.assertEqual(len(json.loads((out / "columns.json").read_text())["headers"]), 36)
            self.assertEqual(json.loads((out / "validation.json").read_text())["document_type"], "lld")
            self.assertEqual(run.extract_config("agentic_plus", "latest", "lld")["data_schema"], SCHEMA)
            self.assertEqual(len(get_profile("application")["columns"]), 23)


if __name__ == "__main__":
    unittest.main()
