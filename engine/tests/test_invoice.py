"""Synthetic invoice observations; never claimed as cloud extraction of the sample."""
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
from invoice.schema import SCHEMA, COLUMNS
from invoice.validation import validate


def evidence():
    text = lambda raw: {"raw": raw, "complete": True}
    raw = {
        "to_name": text("Test Customer Ltd."), "to_address": text("Customer Road 1, Test City"), "to_phone": "+62 (21) 123-4567",
        "from_name": text("Test Supplier Ltd."), "from_address": text("Supplier Road 2, Test City"), "from_phone": None,
        "bank_name": text("Test Bank"), "swift_code": "TESTUS33", "bank_account_number": "0001 2345-6789",
        "invoice_date": "2025-08-07", "due_date": "08/08/2025", "invoice_number": "INV-2025/001_A",
        "item_name": {"table_complete": True, "items": [
            {"row_id": "1", "raw": "Test equipment A", "complete": True},
            {"row_id": "2", "raw": "Test equipment B", "complete": True}]},
        "quantity": [{"row_id": "1", "raw": "2 PCS (20 BAGS packaging)", "value_raw": "2", "unit_raw": "PCS", "other_quantity_note": "20 BAGS packaging"},
                     {"row_id": "2", "raw": "3 Box", "value_raw": "3", "unit_raw": "Box", "other_quantity_note": None}],
        "unit_price": [{"row_id": "1", "amount_raw": "10.00", "currency_raw": "USD", "unit_raw": "PCS"},
                       {"row_id": "2", "amount_raw": "20.00", "currency_raw": "USD", "unit_raw": "BOX"}],
        "subtotal": [{"row_id": "1", "amount_raw": "20.00", "currency_raw": "USD"},
                     {"row_id": "2", "amount_raw": "60.00", "currency_raw": "USD"}],
        "subtotal_all_items": {"amount_raw": "80.00", "currency_raw": "USD"},
        "final_total_amount": {"amount_raw": "88.00", "currency_raw": "USD", "calculation_basis": "full_invoice", "adjustments_complete": True,
                               "adjustments": [{"label": "VAT", "kind": "tax", "amount_raw": "8.00", "currency_raw": "USD", "included_in_base": False}]},
        "claim_note": {"present": False, "note_raw": None, "claim_number_raw": None, "percentage_raw": None, "amount_raw": None,
                       "currency_raw": None, "base_kind": None, "base_amount_raw": None, "base_currency_raw": None, "basis_evidence": None},
    }
    return raw


class InvoiceTests(unittest.TestCase):
    def setUp(self):
        self.raw = evidence()
        self.policy = json.loads((run.ROOT / "invoice/policy.json").read_text())
        self.context = {"invoice_history_complete": True, "invoice_numbers": []}
        self.meta = {"field_metadata": {"document_metadata": {key: {"confidence": .99} for key, _ in COLUMNS}}}

    def report(self):
        return validate(self.raw, self.meta, self.policy, date(2026, 10, 5), validation_context=self.context)

    def claim(self, explicit_base=False):
        self.raw["claim_note"].update(present=True, note_raw="Claim No.2, 60% of Supply Equipment, material arrived at site",
                                    claim_number_raw="2", percentage_raw="60", amount_raw="30.00" if explicit_base else "48.00", currency_raw="USD",
                                    base_kind="explicit_base" if explicit_base else "all_items",
                                    base_amount_raw="50.00" if explicit_base else None, base_currency_raw="USD" if explicit_base else None,
                                    basis_evidence="Explicit eligible equipment base 50.00 USD" if explicit_base else "Claim applies to entire equipment subtotal")
        self.raw["final_total_amount"].update(amount_raw="30.00" if explicit_base else "48.00", calculation_basis="claim_only", adjustments=[])

    def test_all_19_fields_and_independent_calculations_pass(self):
        result = self.report()
        self.assertEqual(result["status"], "PASS", result["fields"])
        self.assertEqual(len(SCHEMA["properties"]), 19)
        self.assertEqual(result["normalized"]["subtotal"][0]["amount"], Decimal("20.00"))
        self.assertEqual(result["normalized"]["subtotal_all_items"]["amount"], Decimal("80.00"))
        self.assertEqual(result["normalized"]["final_total_amount"]["amount"], Decimal("88.00"))
        self.assertEqual(result["normalized"]["bank_account_number"], "000123456789")
        self.assertEqual(result["fields"]["claim_note"]["status"], "NOT_APPLICABLE")
        self.assertEqual(result["fields"]["from_phone"]["status"], "NOT_PRESENT")

    def test_export_has_exact_columns_and_separate_line_item_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            run.export(output, self.report())
            with (output / "result.csv").open(encoding="utf-8-sig", newline="") as f:
                headers, row = list(csv.reader(f))
            self.assertEqual(headers, [label for _, label in COLUMNS])
            self.assertEqual(len(row), 19)
            self.assertEqual(row[8], "000123456789")
            self.assertEqual(len(json.loads(row[12])), 2)
            self.assertEqual(row[16:18], ["USD 80.00", "USD 88.00"])
            with (output / "line_items.csv").open(encoding="utf-8-sig", newline="") as f:
                items = list(csv.DictReader(f))
            self.assertEqual(len(items), 2)
            self.assertEqual(items[0]["printed_subtotal"], items[0]["computed_subtotal"])
            self.assertTrue((output / "calculations.json").exists())

    def test_names_addresses_and_phone_rules(self):
        self.raw["to_name"]["raw"] = "123456"
        self.raw["from_name"]["raw"] = "!!!"
        self.raw["to_address"]["complete"] = False
        self.raw["from_address"]["complete"] = None
        self.raw["to_phone"] = "CALL 123"
        self.raw["from_phone"] = "+62 (123"
        result = self.report()
        for key in ["to_name", "from_name", "to_address", "to_phone", "from_phone"]:
            self.assertEqual(result["fields"][key]["status"], "FAIL")
        self.assertEqual(result["fields"]["from_address"]["status"], "REVIEW")

    def test_phone_country_prefix_in_parentheses_and_address_spacing(self):
        self.raw["to_phone"] = "(+62) 21-1234567"
        self.raw["from_address"]["raw"] = "  Road  1 , Building 2 ; Test City  "
        result = self.report()
        self.assertEqual(result["fields"]["to_phone"]["status"], "PASS")
        self.assertEqual(result["normalized"]["from_address"], "Road 1, Building 2; Test City")
        self.assertEqual(result["raw"]["from_address"]["raw"], self.raw["from_address"]["raw"])

    def test_bic_structure_case_country_and_account_normalization(self):
        for value in ["testus33", "TEST US33", "TEST1233", "TESTZZ33", "123"]:
            with self.subTest(value=value):
                self.raw["swift_code"] = value
                self.assertEqual(self.report()["fields"]["swift_code"]["status"], "FAIL")
        self.raw["swift_code"] = "A1B2US33"
        self.assertEqual(self.report()["fields"]["swift_code"]["status"], "PASS")
        self.raw["bank_account_number"] = "00AB-0012"
        result = self.report()
        self.assertEqual(result["normalized"]["bank_account_number"], "00AB0012")
        self.assertEqual(result["fields"]["bank_account_number"]["status"], "REVIEW")
        self.policy["account_storage_mode"] = "numeric_only"
        self.assertEqual(self.report()["fields"]["bank_account_number"]["status"], "FAIL")

    def test_date_business_days_future_and_due_order(self):
        for value in ["04/10/2026", "06/10/2026", "31/02/2025", "01/01/2025"]:
            with self.subTest(value=value):
                self.raw["invoice_date"] = value
                self.assertEqual(self.report()["fields"]["invoice_date"]["status"], "FAIL")
        self.raw["invoice_date"] = "2025-08-07"
        self.raw["due_date"] = "06/08/2025"
        self.assertIn("DUE_DATE_BEFORE_INVOICE_DATE", [x["code"] for x in self.report()["fields"]["due_date"]["issues"]])
        self.raw["due_date"] = "06/10/2026"
        self.assertEqual(self.report()["fields"]["due_date"]["status"], "FAIL")

    def test_invoice_history_uniqueness_and_missing_history(self):
        self.context["invoice_numbers"] = ["INV-2025/001_A"]
        self.assertEqual(self.report()["fields"]["invoice_number"]["status"], "FAIL")
        self.context = {}
        self.assertEqual(self.report()["fields"]["invoice_number"]["status"], "REVIEW")
        self.context = {"invoice_numbers": [123]}
        with self.assertRaises(ValueError):
            self.report()

    def test_misaligned_or_duplicate_rows_never_get_zipped_silently(self):
        self.raw["quantity"].reverse()
        result = self.report()
        self.assertEqual(result["fields"]["quantity"]["status"], "FAIL")
        self.assertEqual(result["normalized"]["subtotal"], [])
        self.assertIsNone(result["normalized"]["subtotal_all_items"]["amount"])

    def test_packaging_count_does_not_replace_main_quantity(self):
        result = self.report()
        self.assertEqual(result["normalized"]["quantity"][0]["value"], 2)
        self.assertEqual(result["normalized"]["quantity"][0]["other_quantity_note"], "20 BAGS packaging")
        self.raw["quantity"][0]["value_raw"] = "20"
        self.assertEqual(self.report()["fields"]["quantity"]["status"], "FAIL")

    def test_quantity_integer_positive_and_price_unit_must_agree(self):
        for value in ["-2", "0", "2.5"]:
            with self.subTest(value=value):
                self.raw["quantity"][0].update(raw=value + " PCS", value_raw=value)
                self.assertEqual(self.report()["fields"]["quantity"]["status"], "FAIL")
        self.raw = evidence()
        self.raw["quantity"][0]["unit_raw"] = "BOX"
        result = self.report()
        self.assertEqual(result["fields"]["quantity"]["status"], "FAIL")
        self.assertIsNone(result["normalized"]["subtotal"][0]["amount"])

    def test_ambiguous_separator_is_reviewed_without_guessing(self):
        self.raw["unit_price"][0]["amount_raw"] = "1,350"
        result = self.report()
        self.assertEqual(result["fields"]["unit_price"]["status"], "REVIEW")
        self.assertIsNone(result["normalized"]["unit_price"][0]["amount"])
        self.assertEqual(result["numeric_candidates"]["unit_price[1]"], {"en_US": Decimal("1350"), "id_ID": Decimal("1.350")})

    def test_mixed_separator_overrides_still_detect_printed_arithmetic_mismatch(self):
        for key in ["quantity", "unit_price", "subtotal"]:
            self.raw[key] = self.raw[key][:1]
        self.raw["item_name"]["items"] = self.raw["item_name"]["items"][:1]
        self.raw["quantity"][0].update(raw="104MT (TOTAL 4160 BAGS)", value_raw="104", unit_raw="MT")
        self.raw["unit_price"][0].update(amount_raw="1,350", unit_raw="MT")
        self.raw["subtotal"][0]["amount_raw"] = "280.800"
        self.policy["field_number_locales"] = {"unit_price": "en_US", "subtotal": "id_ID"}
        result = self.report()
        self.assertEqual(result["normalized"]["subtotal"][0]["amount"], Decimal("140400.00"))
        self.assertEqual(result["line_items"][0]["printed_subtotal"], Decimal("280800"))
        self.assertEqual(result["fields"]["subtotal"]["status"], "FAIL")
        self.assertEqual(result["raw"]["subtotal"][0]["amount_raw"], "280.800")

    def test_wrong_printed_amount_cannot_override_calculated_subtotal(self):
        self.raw["subtotal"][0]["amount_raw"] = "999.00"
        result = self.report()
        self.assertEqual(result["normalized"]["subtotal"][0]["amount"], Decimal("20.00"))
        self.assertEqual(result["normalized"]["subtotal_all_items"]["amount"], Decimal("80.00"))
        self.assertEqual(result["line_items"][0]["difference"], Decimal("979.00"))
        self.assertEqual(result["fields"]["subtotal"]["status"], "FAIL")

    def test_one_cent_difference_fails_under_default_exact_match_policy(self):
        self.raw["subtotal"][0]["amount_raw"] = "20.01"
        self.assertEqual(self.report()["fields"]["subtotal"]["status"], "FAIL")

    def test_missing_printed_totals_are_not_fabricated_as_evidence(self):
        self.raw["subtotal_all_items"] = {"amount_raw": None, "currency_raw": None}
        self.raw["final_total_amount"].update(amount_raw=None, currency_raw=None)
        result = self.report()
        self.assertEqual(result["normalized"]["subtotal_all_items"]["amount"], Decimal("80.00"))
        self.assertIsNone(result["raw"]["subtotal_all_items"]["amount_raw"])
        self.assertEqual(result["fields"]["subtotal_all_items"]["status"], "FAIL")
        self.assertEqual(result["fields"]["final_total_amount"]["status"], "FAIL")

    def test_incomplete_table_prevents_whole_invoice_calculation(self):
        self.raw["item_name"]["table_complete"] = False
        result = self.report()
        self.assertIsNone(result["normalized"]["subtotal_all_items"]["amount"])
        self.assertIsNone(result["normalized"]["final_total_amount"]["amount"])
        self.assertEqual(result["status"], "REVIEW")

    def test_negative_zero_price_and_mixed_currency(self):
        for value in ["0", "-1"]:
            self.raw["unit_price"][0]["amount_raw"] = value
            self.assertEqual(self.report()["fields"]["unit_price"]["status"], "FAIL")
        self.raw = evidence()
        self.raw["unit_price"][1]["currency_raw"] = self.raw["subtotal"][1]["currency_raw"] = "EUR"
        result = self.report()
        self.assertEqual(result["fields"]["subtotal_all_items"]["status"], "FAIL")
        self.assertIsNone(result["normalized"]["subtotal_all_items"]["amount"])

    def test_bare_dollar_currency_is_not_assumed_to_be_usd(self):
        self.raw["unit_price"][0]["currency_raw"] = "$"
        result = self.report()
        self.assertIsNone(result["normalized"]["unit_price"][0]["currency"])
        self.assertEqual(result["fields"]["unit_price"]["status"], "REVIEW")

    def test_tax_fee_discount_and_final_total_are_checked(self):
        self.raw["final_total_amount"]["adjustments"].extend([
            {"label": "Shipping", "kind": "shipping", "amount_raw": "2.00", "currency_raw": "USD", "included_in_base": False},
            {"label": "Discount", "kind": "discount", "amount_raw": "-5.00", "currency_raw": "USD", "included_in_base": False}])
        self.raw["final_total_amount"]["amount_raw"] = "85.00"
        self.assertEqual(self.report()["normalized"]["final_total_amount"]["amount"], Decimal("85.00"))
        self.raw["final_total_amount"]["amount_raw"] = "90.00"
        self.assertEqual(self.report()["fields"]["final_total_amount"]["status"], "FAIL")
        self.raw["final_total_amount"]["adjustments_complete"] = None
        self.assertIsNone(self.report()["normalized"]["final_total_amount"]["amount"])

    def test_already_included_tax_is_not_added_twice(self):
        self.raw["final_total_amount"]["amount_raw"] = "80.00"
        self.raw["final_total_amount"]["adjustments"][0]["included_in_base"] = True
        result = self.report()
        self.assertEqual(result["normalized"]["final_total_amount"]["amount"], Decimal("80.00"))
        self.assertEqual(result["fields"]["final_total_amount"]["status"], "PASS")

    def test_unclear_tax_inclusion_does_not_produce_a_guessed_final_total(self):
        self.raw["final_total_amount"]["adjustments"][0]["included_in_base"] = None
        result = self.report()
        self.assertIsNone(result["normalized"]["final_total_amount"]["amount"])
        self.assertEqual(result["fields"]["final_total_amount"]["status"], "REVIEW")

    def test_claim_60_percent_and_claim_only_final_total(self):
        self.claim()
        result = self.report()
        self.assertEqual(result["status"], "PASS", result["fields"])
        self.assertEqual(result["normalized"]["claim_note"]["expected_amount"], Decimal("48.00"))
        self.assertEqual(result["normalized"]["final_total_amount"]["amount"], Decimal("48.00"))
        self.raw["claim_note"]["amount_raw"] = "40.00"
        self.assertEqual(self.report()["fields"]["claim_note"]["status"], "FAIL")

    def test_claim_explicit_eligible_base_and_unknown_base(self):
        self.claim(explicit_base=True)
        result = self.report()
        self.assertEqual(result["normalized"]["claim_note"]["expected_amount"], Decimal("30.00"))
        self.assertEqual(result["status"], "PASS")
        self.raw["claim_note"]["base_kind"] = "uncertain"
        result = self.report()
        self.assertIsNone(result["normalized"]["claim_note"]["expected_amount"])
        self.assertEqual(result["fields"]["claim_note"]["status"], "REVIEW")

    def test_claim_number_percentage_and_presence(self):
        self.claim()
        self.raw["claim_note"].update(claim_number_raw="3", percentage_raw="50")
        self.assertEqual(self.report()["fields"]["claim_note"]["status"], "FAIL")
        self.raw = evidence()
        self.raw["claim_note"]["present"] = None
        self.assertEqual(self.report()["fields"]["claim_note"]["status"], "REVIEW")
        self.policy["claim_required"] = True
        self.raw["claim_note"]["present"] = False
        self.assertEqual(self.report()["fields"]["claim_note"]["status"], "FAIL")

    def test_low_or_unavailable_confidence_does_not_pass(self):
        self.meta["field_metadata"]["document_metadata"]["item_name"]["confidence"] = .4
        self.assertEqual(self.report()["fields"]["item_name"]["status"], "REVIEW")
        self.meta = {}
        self.assertEqual(self.report()["status"], "REVIEW")

    def test_invoice_replay_uses_19_column_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            replay = root / "extract.json"
            replay.write_text(json.dumps({"status": "COMPLETED", "extract_result": self.raw, "extract_metadata": self.meta}))
            output = root / "output"
            self.assertEqual(run.main(["--document-type", "invoice", "--replay", str(replay), "--output", str(output), "--as-of", "2026-10-05"]), 0)
            self.assertEqual(len(json.loads((output / "columns.json").read_text())["headers"]), 19)
            self.assertEqual(json.loads((output / "validation.json").read_text())["document_type"], "invoice")


if __name__ == "__main__":
    unittest.main()
