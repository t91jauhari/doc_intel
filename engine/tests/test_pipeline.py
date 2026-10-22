"""Offline tests: synthetic evidence, never an extraction/ground truth of Poko."""
import csv
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from llama_cloud import LlamaCloud
import run
from schema import COLUMNS, SCHEMA
from validation import parse_date, parse_number, validate, check_schema
from context import resolve_checkbox


def empty(schema):
    if schema["type"] == "object":
        return {k: empty(v) for k, v in schema["properties"].items()}
    return None


def option(label, selected=False, tail=False):
    return {"label": label, "state": "selected" if selected else "unselected",
            "local_mark_present": selected, "mark_type": "tick" if selected else "none",
            "tail_overlap_only": tail,
            "evidence": "distinct short tick body in this checkbox" if selected else "no own local mark; trailing stroke only" if tail else "empty checkbox, no selection mark"}


def evidence():
    raw = empty(SCHEMA)
    raw.update(branch="KCP Test", transaction_date="05/08/2025", currency="USD", exchange_rate="16.000",
               swift_code="TESTUS33XXX", beneficiary_account_number="001234-AB",
               remitter_account_number="000123", transaction_account_number="000987",
               source_of_funds="Gaji", transaction_purpose="Pembayaran jasa", transaction_bank_name=None,
               notes="Reference 123")
    raw["payment_type"]["selected"] = ["DEBIT REKENING"]
    raw["transaction_type"].update(selected=["SWIFT"])
    for key in ["beneficiary", "remitter"]:
        raw[key].update(full_text="Test Person\nTest Street\n+62-123", name="Test Person", address="Test Street", phone="+62-123")
    raw["beneficiary_bank"].update(name="Test Bank", branch="Test City")
    raw["amount"].update(raw="150.000", currency="USD")
    raw["charges"].update(raw="25", currency="USD", selected=["Tunai"])
    raw["total_amount"].update(raw="150.025", currency="USD")
    raw["amount_in_words"].update(raw="Seratus lima puluh ribu dua puluh lima dolar Amerika Serikat", language="id", complete=True)
    raw["customer_signature"].update(present=True, handwritten=True)
    raw["bank_approval"].update(present=True, stamp_present=True, stamp_text="TEST BANK")
    raw["payment_type"].update(options_complete=True, options=[option("Cek/BG"), option("Tunai"), option("DEBIT REKENING", True)])
    raw["transaction_type"].update(options_complete=True, options=[option(x, x == "SWIFT") for x in ["LLG", "INKASI", "RTGS", "SWIFT", "Pemindahbukuan", "Wessel", "Lainnya"]])
    raw["charges"].update(options_complete=True, options=[option("Tunai", True), option("Debet Rekening")])
    return raw


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads((run.ROOT / "policy.json").read_text())
        self.policy["bank_stamp_rule_confirmed"] = True
        self.raw = evidence()
        self.meta = {"field_metadata": {"document_metadata": {k: {"confidence": 0.99, "citation": [{"page": 1, "matching_text": "synthetic"}]} for k, _ in COLUMNS}}}

    def report(self):
        return validate(self.raw, self.meta, self.policy, date(2026, 10, 5))

    def test_valid_and_raw_preserved(self):
        result = self.report()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["normalized"]["amount"], Decimal("150000"))
        self.assertEqual(result["raw"]["amount"]["raw"], "150.000")
        self.assertEqual(result["normalized"]["beneficiary_account_number"], "001234-AB")
        self.assertEqual(result["normalized"]["payment_type"], "Debet Rekening")

    def test_numeric_formats(self):
        self.assertEqual(parse_number("100.817,90"), Decimal("100817.90"))
        self.assertEqual(parse_number("280.80", "en_US"), Decimal("280.80"))
        for bad in ["280.80", "3.248.", "1.2E+13", "NaN", "0", "-1", "15.00.000", "1 2 3"]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse_number(bad)

    def test_dates(self):
        for raw in ["1/6/1993", "01-06-1993", "01-Jun-1993", "1993-06-01", "1 Juni 1993"]:
            self.assertEqual(parse_date(raw), date(1993, 6, 1))
        self.assertEqual(parse_date("05/08/25"), date(2025, 8, 5))
        for raw in ["32/08/2025", "29/02/2025", "Mei 2025", "05/08"]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_date(raw)

    def test_future_weekend_and_public_holiday(self):
        for raw, code in [("06/10/2026", "FUTURE_DATE"), ("04/10/2026", "WEEKEND"), ("01/01/2025", "INDONESIAN_HOLIDAY_OR_JOINT_LEAVE")]:
            self.raw["transaction_date"] = raw
            self.assertIn(code, [i["code"] for i in self.report()["fields"]["transaction_date"]["issues"]])

    def test_uncertainty_requires_review(self):
        self.raw["amount"]["currency"] = None
        self.raw["customer_signature"]["present"] = None
        self.policy["bank_stamp_rule_confirmed"] = False
        result = self.report()
        self.assertEqual(result["status"], "REVIEW")
        self.assertEqual(result["fields"]["total_amount"]["status"], "REVIEW")
        self.assertEqual(result["fields"]["bank_approval"]["status"], "REVIEW")

    def test_mismatch_and_multi_checkbox(self):
        self.raw["total_amount"]["raw"] = "200.000"
        self.raw["payment_type"]["selected"] = ["Tunai", "Debet Rekening"]
        self.raw["payment_type"]["options"] = [option("Cek/BG"), option("Tunai", True), option("Debet Rekening", True)]
        result = self.report()
        self.assertEqual(result["fields"]["total_amount"]["status"], "FAIL")
        self.assertEqual(result["fields"]["payment_type"]["status"], "FAIL")

    def test_lainnya_requires_notes_even_if_description_exists(self):
        self.raw["transaction_type"].update(selected=["Lainnya"], other_description="Valas")
        self.raw["transaction_type"]["options"] = [option(x, x == "Lainnya") for x in ["LLG", "INKASI", "RTGS", "SWIFT", "Pemindahbukuan", "Wessel", "Lainnya"]]
        self.raw["notes"] = None
        self.assertEqual(self.report()["fields"]["transaction_type"]["status"], "FAIL")

    def test_zero_missing_and_invalid_signature(self):
        self.raw["charges"]["raw"] = "0"
        self.raw["remitter"]["address"] = None
        self.raw["customer_signature"]["handwritten"] = False
        result = self.report()
        for key in ["charges", "remitter", "customer_signature"]:
            self.assertEqual(result["fields"][key]["status"], "FAIL")

    def test_missing_confidence(self):
        self.meta = {}
        self.assertEqual(self.report()["status"], "REVIEW")

    def test_cross_document_correction_replaces_missing_remitter_address(self):
        # A missing remitter address is replaced with the authoritative eKTP value;
        # provenance is recorded and the field is downgraded from FAIL to REVIEW.
        self.raw["remitter"]["address"] = None
        ctx = {"authoritative": {"address": "Jl. Merdeka No. 10, Jakarta", "name": "Rina Putri"}}
        result = validate(self.raw, self.meta, self.policy, date(2026, 10, 5), validation_context=ctx)
        self.assertEqual(result["normalized"]["remitter"]["address"], "Jl. Merdeka No. 10, Jakarta")
        correction = next(c for c in result["corrections"] if c["field"] == "remitter.address")
        self.assertIsNone(correction["before"])
        self.assertEqual(correction["after"], "Jl. Merdeka No. 10, Jakarta")
        self.assertEqual(correction["method"], "cross_document_ektp_authoritative")
        self.assertTrue(correction["review_required"])
        self.assertEqual(result["fields"]["remitter"]["status"], "REVIEW")
        codes = [i["code"] for i in result["fields"]["remitter"]["issues"]]
        self.assertIn("CROSS_DOCUMENT_CORRECTION_APPLIED", codes)
        self.assertNotIn("ADDRESS_REQUIRED", codes)

    def test_cross_document_correction_skips_good_remitter_value(self):
        # A good, high-confidence remitter value is never overwritten by the cross-source.
        ctx = {"authoritative": {"address": "Jl. Lain No. 1", "name": "Bukan Rina"}}
        result = validate(self.raw, self.meta, self.policy, date(2026, 10, 5), validation_context=ctx)
        self.assertEqual(result["normalized"]["remitter"]["address"], "Test Street")
        self.assertEqual(result["normalized"]["remitter"]["name"], "Test Person")
        self.assertFalse(any(c["field"].startswith("remitter.") for c in result["corrections"]))

    def test_cross_document_correction_replaces_low_confidence_remitter_address(self):
        # A low-confidence remitter address is replaced with the authoritative value.
        self.meta["field_metadata"]["document_metadata"]["remitter"] = {
            "confidence": 0.2, "citation": [{"page": 1, "matching_text": "synthetic"}]
        }
        ctx = {"authoritative": {"address": "Jl. Merdeka No. 10, Jakarta"}}
        result = validate(self.raw, self.meta, self.policy, date(2026, 10, 5), validation_context=ctx)
        self.assertEqual(result["normalized"]["remitter"]["address"], "Jl. Merdeka No. 10, Jakarta")
        self.assertEqual(result["fields"]["remitter"]["status"], "REVIEW")
        self.assertTrue(any(c["field"] == "remitter.address" for c in result["corrections"]))

    def test_account_is_not_numeric(self):
        self.raw["beneficiary_account_number"] = 123
        with self.assertRaises(ValueError):
            check_schema(self.raw)

    def test_exports_keep_duplicate_headers_and_exact_decimal(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            run.export(out, self.report())
            with (out / "result.csv").open(encoding="utf-8-sig", newline="") as f:
                header, values = list(csv.reader(f))
            self.assertEqual(len(header), 23)
            self.assertEqual(header.count("A/C no"), 2)
            self.assertEqual(values[7], "001234-AB")
            self.assertEqual(values[9], "000123")
            self.assertEqual(json.loads((out / "normalized.json").read_text())["amount"], 150000)

    def test_approved_alias_changes_normalized_bank_only(self):
        directory = json.loads((run.ROOT / "name_directory.json").read_text())
        self.raw["beneficiary_bank"]["name"] = "EAST WEST PANK"
        result = validate(self.raw, self.meta, self.policy, date(2026, 10, 5), directory)
        self.assertEqual(result["raw"]["beneficiary_bank"]["name"], "EAST WEST PANK")
        self.assertEqual(self.raw["beneficiary_bank"]["name"], "EAST WEST PANK")
        self.assertEqual(result["normalized"]["beneficiary_bank"]["name"], "EAST WEST BANK")
        self.assertEqual(result["corrections"][0]["method"], "approved_alias")
        self.assertEqual(result["fields"]["beneficiary_bank"]["status"], "REVIEW")
        self.assertEqual(result["normalized"]["beneficiary_account_number"], "001234-AB")

    def test_unapproved_fuzzy_name_is_suggested_not_changed(self):
        directory = json.loads((run.ROOT / "name_directory.json").read_text())
        self.raw["beneficiary_bank"]["name"] = "EAST WEST BANC"
        result = validate(self.raw, self.meta, self.policy, date(2026, 10, 5), directory)
        self.assertEqual(result["normalized"]["beneficiary_bank"]["name"], "EAST WEST BANC")
        self.assertEqual(result["correction_suggestions"][0]["candidates"], ["EAST WEST BANK"])

    def test_verified_bic_conflict_blocks_correction(self):
        directory = {"bank_names": [{"name": "EAST WEST BANK", "aliases": ["EAST WEST PANK"], "bic_prefixes": ["FAKEUS"]}]}
        self.raw["beneficiary_bank"]["name"] = "EAST WEST PANK"
        result = validate(self.raw, self.meta, self.policy, date(2026, 10, 5), directory)
        self.assertEqual(result["normalized"]["beneficiary_bank"]["name"], "EAST WEST PANK")
        self.assertIn("CORRECTION_CONFLICTS_WITH_VERIFIED_BIC", [x["code"] for x in result["fields"]["beneficiary_bank"]["issues"]])

    def test_conflicting_alias_directory_does_not_pick_a_bank(self):
        directory = {"bank_names": [{"name": "TEST BANK A", "aliases": ["TEST PANK"]}, {"name": "TEST BANK B", "aliases": ["TEST PANK"]}]}
        self.raw["beneficiary_bank"]["name"] = "TEST PANK"
        result = validate(self.raw, self.meta, self.policy, date(2026, 10, 5), directory)
        self.assertEqual(result["normalized"]["beneficiary_bank"]["name"], "TEST PANK")
        self.assertIn("CORRECTION_DIRECTORY_CONFLICT", [x["code"] for x in result["fields"]["beneficiary_bank"]["issues"]])

    def test_long_debit_tick_tail_does_not_select_tunai(self):
        self.raw["payment_type"].update(selected=["Tunai", "Debet Rekening"],
            options=[option("Cek/BG"), option("Tunai", tail=True), option("Debet Rekening", True)])
        result = self.report()
        self.assertEqual(result["normalized"]["payment_type"], "Debet Rekening")
        self.assertEqual(result["raw"]["payment_type"]["selected"], ["Tunai", "Debet Rekening"])
        self.assertTrue(result["checkbox_resolutions"]["payment_type"]["reconciled"])
        self.assertEqual(result["fields"]["payment_type"]["status"], "REVIEW")

    def test_reverse_long_tunai_tick_does_not_select_debit(self):
        self.raw["payment_type"].update(selected=["Tunai"],
            options=[option("Cek/BG"), option("Tunai", True), option("Debet Rekening", tail=True)])
        self.assertEqual(self.report()["normalized"]["payment_type"], "Tunai")
        self.assertEqual(self.report()["fields"]["payment_type"]["status"], "PASS")

    def test_ambiguous_local_origin_requires_review(self):
        self.raw["payment_type"]["options"][2]["local_mark_present"] = None
        result = self.report()
        self.assertIsNone(result["normalized"]["payment_type"])
        self.assertEqual(result["fields"]["payment_type"]["status"], "REVIEW")

    def test_legacy_response_without_local_evidence_is_replayable(self):
        for key in ["payment_type", "transaction_type", "charges"]:
            del self.raw[key]["options"]
            del self.raw[key]["options_complete"]
        result = self.report()
        self.assertEqual(result["normalized"]["payment_type"], "Debet Rekening")
        self.assertEqual(result["fields"]["payment_type"]["status"], "REVIEW")

    def test_contradictory_local_mark_and_tail_only_is_not_auto_selected(self):
        self.raw["charges"]["options"][0]["tail_overlap_only"] = True
        result = self.report()
        self.assertIsNone(result["normalized"]["charges"]["payment_method"])
        self.assertEqual(result["fields"]["charges"]["status"], "REVIEW")

    def test_cli_replay_applies_alias_and_preserves_raw_in_export(self):
        self.raw["beneficiary_bank"]["name"] = "EAST WEST PANK"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            replay = path / "extract.json"
            replay.write_text(json.dumps({"status": "COMPLETED", "extract_result": self.raw, "extract_metadata": self.meta}))
            output = path / "outputs"
            self.assertEqual(run.main(["--replay", str(replay), "--output", str(output), "--as-of", "2026-10-05"]), 0)
            raw = json.loads((output / "raw.json").read_text())
            normalized = json.loads((output / "normalized.json").read_text())
            self.assertEqual(raw["beneficiary_bank"]["name"], "EAST WEST PANK")
            self.assertEqual(normalized["beneficiary_bank"]["name"], "EAST WEST BANK")
            self.assertEqual(json.loads((output / "corrections.json").read_text())["applied"][0]["method"], "approved_alias")
            with (output / "result.csv").open(encoding="utf-8-sig", newline="") as f:
                header, values = list(csv.reader(f))
            self.assertEqual(len(header), 23)
            self.assertIn("EAST WEST BANK", values[5])


class SDKContractTests(unittest.TestCase):
    def test_explicit_dotenv_overrides_stale_environment(self):
        with tempfile.TemporaryDirectory() as folder:
            env = Path(folder) / ".env"
            env.write_text('LLAMA_CLOUD_API_KEY=" llx-file-test "\nLLAMA_CLOUD_BASE_URL=\n', encoding="utf-8-sig")
            with patch.dict(run.os.environ, {"LLAMA_CLOUD_API_KEY": "llx-old-environment", "LLAMA_CLOUD_BASE_URL": "https://old.example"}):
                config = run.settings(env)
                self.assertEqual(config["LLAMA_CLOUD_API_KEY"], "llx-file-test")
                self.assertEqual(config["LLAMA_CLOUD_BASE_URL"], "")

    def test_bearer_prefix_rejected_before_network(self):
        with tempfile.TemporaryDirectory() as folder:
            env = Path(folder) / ".env"
            env.write_text("LLAMA_CLOUD_API_KEY=Bearer llx-test\n")
            with self.assertRaisesRegex(ValueError, "without 'Bearer '"):
                run.settings(env)

    def test_check_auth_makes_one_get_and_never_uploads(self):
        requests = []
        def handler(request):
            requests.append(request)
            self.assertEqual(request.method, "GET")
            self.assertEqual(request.url.path, "/api/v1/beta/files")
            self.assertEqual(request.headers["authorization"], "Bearer llx-file-test")
            return httpx.Response(200, json={"items": [], "next_page_token": None})
        with tempfile.TemporaryDirectory() as folder, httpx.Client(transport=httpx.MockTransport(handler)) as http:
            env = Path(folder) / ".env"
            env.write_text("LLAMA_CLOUD_API_KEY=llx-file-test\nLLAMA_CLOUD_BASE_URL=\nLLAMA_CLOUD_PROJECT_ID=\nLLAMA_CLOUD_ORGANIZATION_ID=\n")
            client = LlamaCloud(api_key="llx-file-test", http_client=http, max_retries=0)
            with patch.object(run, "LlamaCloud", return_value=client):
                self.assertEqual(run.main(["--check-auth", "--env-file", str(env), "--output", str(Path(folder) / "output")]), 0)
        self.assertEqual(len(requests), 1)

    def test_real_sdk_sends_parse_id_and_expands_metadata(self):
        captured = []

        def handler(request):
            body = json.loads(request.content) if request.content else None
            captured.append((request.method, request.url.path, dict(request.url.params), body))
            if request.url.path == "/api/v2/parse" and request.method == "POST":
                response = {"id": "pjb-test", "project_id": "prj-test", "status": "PENDING"}
            elif request.url.path == "/api/v2/parse/pjb-test":
                response = {"job": {"id": "pjb-test", "project_id": "prj-test", "status": "COMPLETED"}}
            elif request.url.path == "/api/v2/extract" and request.method == "POST":
                response = {"id": "ext-test", "project_id": "prj-test", "status": "PENDING", "file_input": "pjb-test", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"}
            elif request.url.path == "/api/v2/extract/ext-test":
                response = {"id": "ext-test", "project_id": "prj-test", "status": "COMPLETED", "file_input": "pjb-test", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z", "extract_result": evidence(), "extract_metadata": {"field_metadata": {"document_metadata": {}}}}
            else:
                raise AssertionError(f"Unexpected request {request.url}")
            return httpx.Response(200, json=response)

        with tempfile.TemporaryDirectory() as folder, httpx.Client(transport=httpx.MockTransport(handler)) as http:
            with LlamaCloud(api_key="synthetic-test-key", http_client=http, max_retries=0) as client:
                parse = client.parsing.create(file_id="dfl-test", **run.parse_config("agentic_plus", "latest"))
                run.poll(client, "parse", parse.id, {}, Path(folder), 10, .001)
                extract = client.extract.create(file_input=parse.id, configuration=run.extract_config("agentic_plus", "latest"))
                final = run.poll(client, "extract", extract.id, {}, Path(folder), 10, .001)
                self.assertEqual(final.extract_result["beneficiary_account_number"], "001234-AB")
        creation = next(x for x in captured if x[0] == "POST" and x[1] == "/api/v2/extract")
        self.assertEqual(creation[3]["file_input"], "pjb-test")
        self.assertTrue(any("expand" in x[2] and "extract_metadata" in x[2]["expand"] for x in captured))


if __name__ == "__main__":
    unittest.main()
