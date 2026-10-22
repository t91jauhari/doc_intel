"""Mixed batches exercised offline through the actual single-document validator/export."""
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import httpx
from llama_cloud import AuthenticationError, LlamaCloud

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import batch
import run
from test_lld import evidence as lld_evidence
from test_pipeline import evidence as application_evidence
from test_invoice import evidence as invoice_evidence
from test_valas2 import evidence as valas2_evidence
from test_valas1 import evidence as valas1_evidence
from test_ektp import evidence as ektp_evidence
from profiles import get_profile


def csv_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def grouped_rows(output):
    rows = []
    for profile in batch.PROFILE_NAMES:
        path = output / f"{profile}_result.csv"
        if path.exists():
            rows.extend(csv_rows(path))
    return sorted(rows, key=lambda row: row["output_directory"])


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.samples = self.root / "samples"
        self.samples.mkdir()
        self.output = self.root / "output"

    def files(self, *names):
        for name in names:
            (self.samples / name).write_bytes(b"%PDF-1.4 synthetic upload fixture, not a real scan")

    def args(self, **options):
        from argparse import Namespace
        values = dict(samples_dir=self.samples, output=self.output, env_file=None,
                      name_directory=run.ROOT / "name_directory.json", parse_tier="agentic_plus",
                      extract_tier="agentic_plus", parse_version="latest", extract_version="latest",
                      timeout=1200, poll_interval=3, as_of="2026-10-05", application_policy=None,
                      lld_policy=None, invoice_policy=None, invoice_validation_context=None,
                      valas2_policy=None, valas2_validation_context=None,
                      valas1_policy=None, valas1_validation_context=None,
                      ektp_policy=None, ektp_validation_context=None,
                      validation_context=None, dry_run=False)
        values.update(options)
        return Namespace(**values)

    def replay_document(self, argv, overrides=None):
        argv = list(argv)
        source = Path(argv[argv.index("--pdf") + 1])
        profile = argv[argv.index("--document-type") + 1]
        evidence = {"lld": lld_evidence, "application": application_evidence, "invoice": invoice_evidence, "valas_declaration_2": valas2_evidence, "valas_declaration_1": valas1_evidence, "ektp": ektp_evidence}[profile]()
        if overrides:
            overrides(evidence)
        replay = self.root / (source.name + ".json")
        meta = {"field_metadata": {"document_metadata": {
            k: {"confidence": .99} for k, _ in get_profile(profile)["columns"]}}}
        replay.write_text(json.dumps({"status": "COMPLETED", "extract_result": evidence, "extract_metadata": meta}))
        index = argv.index("--pdf")
        del argv[index:index + 2]
        return run.main(argv + ["--replay", str(replay)])

    def test_discovery_matches_suffixes_case_insensitively_and_ignores_other_files(self):
        self.files("Z_TRANSACTION.PDF", "a_lld.pdf", "invoice.pdf", "old.pdf", "a_lld.pdf.backup", "x_transaction.txt")
        (self.samples / "folder_lld.pdf").mkdir()
        selected, ignored = batch.discover(self.samples)
        self.assertEqual([(p.name, kind) for p, kind in selected], [("a_lld.pdf", "lld"), ("Z_TRANSACTION.PDF", "application")])
        self.assertEqual(len(ignored), 4)

    def test_mixed_batch_has_separate_profile_summaries_and_individual_results(self):
        self.files("01_poko_lld.pdf", "02_poko_transaction.pdf", "invoice.pdf")
        code = batch.process_batch(self.args(), self.replay_document)
        self.assertEqual(code, 0)
        rows = grouped_rows(self.output)
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(rows[0]), 44)
        self.assertEqual(len(rows[1]), 31)
        self.assertFalse((self.output / "combined_result.csv").exists())
        self.assertFalse((self.output / "combined_columns.json").exists())
        self.assertFalse((self.output / "invoice_result.csv").exists())
        self.assertEqual(rows[0]["transaction_value"], "USD 150000")
        self.assertEqual(rows[0]["payer_identification_number"], "0100123456789012")
        self.assertNotIn("amount", rows[0])
        self.assertEqual(rows[1]["amount"], "150000")
        self.assertEqual(rows[1]["beneficiary_account_number"], "001234-AB")
        self.assertNotIn("transaction_value", rows[1])
        for row, count in zip(rows, [36, 23]):
            self.assertEqual(row["processing_status"], "COMPLETED")
            folder = self.output / row["output_directory"]
            with (folder / "result.csv").open(encoding="utf-8-sig", newline="") as f:
                header, values = list(csv.reader(f))
            self.assertEqual(len(header), count)
            self.assertEqual(len(values), count)
            for (key, _), value in zip(get_profile(row["document_type"])["columns"], values):
                self.assertEqual(row[key], value)
            self.assertTrue(row["source_file"].removesuffix(".pdf") in folder.name)
        summary = json.loads((self.output / "summary.json").read_text())
        self.assertEqual(summary["completed"], 2)
        self.assertEqual(summary["errors"], 0)
        self.assertEqual(summary["ignored_files"], ["invoice.pdf"])
        self.assertEqual(set(summary["document_types"]), {"application", "lld"})
        for profile in ("application", "lld"):
            mapping = run.read(self.output / f"{profile}_columns.json")
            self.assertEqual([field["header"] for field in mapping["fields"]],
                             [key for key, _ in get_profile(profile)["columns"]])
            self.assertEqual(summary["document_types"][profile]["total_files"], 1)


    def test_processing_error_keeps_previous_rows_and_continues_next_file(self):
        self.files("1_lld.pdf", "2_transaction.pdf", "3_lld.pdf")
        def process(argv):
            source = Path(argv[argv.index("--pdf") + 1])
            if source.name == "2_transaction.pdf":
                rows = grouped_rows(self.output)
                self.assertEqual(rows[0]["processing_status"], "COMPLETED")
                self.assertEqual(rows[1]["processing_status"], "PROCESSING")
                raise RuntimeError("Synthetic processing failure")
            return self.replay_document(argv)
        self.assertEqual(batch.process_batch(self.args(), process), 1)
        rows = grouped_rows(self.output)
        self.assertEqual([r["processing_status"] for r in rows], ["COMPLETED", "ERROR", "COMPLETED"])
        self.assertEqual(rows[1]["validation_status"], "")
        self.assertEqual(rows[1]["amount"], "")
        self.assertIn("Synthetic processing failure", rows[1]["error"])
        self.assertTrue((self.output / rows[1]["output_directory"] / "error.json").is_file())

    def test_document_validation_failure_is_exported_without_failing_the_batch(self):
        self.files("a_transaction.pdf")
        def process(argv):
            return self.replay_document(argv, lambda raw: raw["customer_signature"].update(handwritten=False))
        self.assertEqual(batch.process_batch(self.args(), process), 0)
        row = grouped_rows(self.output)[0]
        self.assertEqual(row["processing_status"], "COMPLETED")
        self.assertEqual(row["validation_status"], "FAIL")
        self.assertIn("customer_signature", row["failed_fields"])
        self.assertTrue((self.output / row["output_directory"] / "result.csv").exists())

    def test_api_error_body_is_not_written_to_csv_or_error_file(self):
        self.files("a_lld.pdf")
        def process(argv):
            response = httpx.Response(401, request=httpx.Request("POST", "https://example.test"))
            raise AuthenticationError("SECRET_KEY_AND_PRIVATE_BODY", response=response, body={"private": "SECRET_KEY_AND_PRIVATE_BODY"})
        self.assertEqual(batch.process_batch(self.args(), process), 1)
        row = grouped_rows(self.output)[0]
        self.assertIn("status=401", row["error"])
        self.assertNotIn("SECRET_KEY", (self.output / "lld_result.csv").read_text())
        self.assertNotIn("SECRET_KEY", (self.output / row["output_directory"] / "error.json").read_text())

    def test_interrupt_preserves_completed_rows_and_remaining_pending_rows(self):
        self.files("1_transaction.pdf", "2_lld.pdf", "3_lld.pdf")
        def process(argv):
            if Path(argv[argv.index("--pdf") + 1]).name == "2_lld.pdf":
                raise KeyboardInterrupt()
            return self.replay_document(argv)
        self.assertEqual(batch.process_batch(self.args(), process), 130)
        self.assertEqual([row["processing_status"] for row in grouped_rows(self.output)],
                         ["COMPLETED", "INTERRUPTED", "PENDING"])

    def test_cli_dry_run_routes_each_filename_to_its_own_schema(self):
        self.files("a_transaction.pdf", "b_lld.pdf")
        with patch.object(run, "LlamaCloud", side_effect=AssertionError("Dry run attempted a network call")):
            self.assertEqual(run.main(["--batch", "--samples-dir", str(self.samples), "--output", str(self.output), "--dry-run"]), 0)
        rows = grouped_rows(self.output)
        self.assertEqual([row["processing_status"] for row in rows], ["DRY_RUN", "DRY_RUN"])
        for row, count in zip(rows, [23, 36]):
            folder = self.output / row["output_directory"]
            schema = json.loads((folder / "schema.json").read_text())
            self.assertEqual(len(schema["properties"]), count)
            config = json.loads((folder / "request_config.json").read_text())
            self.assertEqual(config["parse"]["tier"], "agentic_plus")
            self.assertEqual(config["extract"]["tier"], "agentic_plus")

    def test_per_profile_policy_and_context_are_forwarded_correctly(self):
        args = self.args(application_policy=Path("app-policy.json"), lld_policy=Path("lld-policy.json"),
                         invoice_policy=Path("invoice-policy.json"), invoice_validation_context=Path("invoice-history.json"),
                         valas2_policy=Path("valas2-policy.json"), valas2_validation_context=Path("stamp-checks.json"),
                         valas1_policy=Path("valas1-policy.json"), valas1_validation_context=Path("valas1-stamp-checks.json"),
                         ektp_policy=Path("ektp-policy.json"), ektp_validation_context=Path("signature-comparisons.json"),
                         validation_context=Path("history.json"), env_file=Path(".env"))
        app = batch.document_arguments(args, Path("test_transaction.pdf"), "application", self.output)
        lld = batch.document_arguments(args, Path("test_lld.pdf"), "lld", self.output)
        self.assertEqual(app[app.index("--policy") + 1], "app-policy.json")
        self.assertNotIn("--validation-context", app)
        self.assertEqual(lld[lld.index("--policy") + 1], "lld-policy.json")
        self.assertEqual(lld[lld.index("--validation-context") + 1], "history.json")
        invoice = batch.document_arguments(args, Path("test_invoice.pdf"), "invoice", self.output)
        self.assertEqual(invoice[invoice.index("--policy") + 1], "invoice-policy.json")
        self.assertEqual(invoice[invoice.index("--validation-context") + 1], "invoice-history.json")
        valas2 = batch.document_arguments(args, Path("test_valas2.pdf"), "valas_declaration_2", self.output)
        self.assertEqual(valas2[valas2.index("--policy") + 1], "valas2-policy.json")
        self.assertEqual(valas2[valas2.index("--validation-context") + 1], "stamp-checks.json")
        valas1 = batch.document_arguments(args, Path("test_valas1.pdf"), "valas_declaration_1", self.output)
        self.assertEqual(valas1[valas1.index("--policy") + 1], "valas1-policy.json")
        self.assertEqual(valas1[valas1.index("--validation-context") + 1], "valas1-stamp-checks.json")
        ektp = batch.document_arguments(args, Path("test_ektp.pdf"), "ektp", self.output)
        self.assertEqual(ektp[ektp.index("--policy") + 1], "ektp-policy.json")
        self.assertEqual(ektp[ektp.index("--validation-context") + 1], "signature-comparisons.json")




    def test_real_sdk_batch_uploads_each_file_once_and_uses_matching_parse_and_extract_schema(self):
        self.files("a_lld.pdf", "b_transaction.pdf", "c_invoice.pdf", "d_valas2.pdf", "e_valas1.pdf", "f_ektp.pdf")
        requests, uploads, parses, extracts = [], {}, {}, {}
        def handler(request):
            requests.append((request.method, request.url.path))
            path = request.url.path
            if path == "/api/v1/beta/files" and request.method == "POST":
                identifier = f"dfl-{len(uploads) + 1}"
                profile = next(name for suffix, name in batch.SUFFIXES.items() if suffix.encode() in request.content)
                uploads[identifier] = profile
                response = {"id": identifier, "name": profile + ".pdf", "purpose": "parse"}
            elif path == "/api/v2/parse" and request.method == "POST":
                body = json.loads(request.content)
                self.assertEqual(body["tier"], "agentic_plus")
                identifier = f"pjb-{len(parses) + 1}"
                parses[identifier] = uploads[body["file_id"]]
                response = {"id": identifier, "project_id": "prj-test", "status": "PENDING"}
            elif path.startswith("/api/v2/parse/"):
                response = {"job": {"id": path.rsplit("/", 1)[1], "project_id": "prj-test", "status": "COMPLETED"}}
            elif path == "/api/v2/extract" and request.method == "POST":
                body = json.loads(request.content)
                profile = parses[body["file_input"]]
                self.assertEqual(body["configuration"]["tier"], "agentic_plus")
                self.assertEqual(body["configuration"]["data_schema"], get_profile(profile)["schema"])
                identifier = f"ext-{len(extracts) + 1}"
                extracts[identifier] = (profile, body["file_input"])
                response = {"id": identifier, "project_id": "prj-test", "status": "PENDING", "file_input": body["file_input"],
                            "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"}
            elif path.startswith("/api/v2/extract/"):
                identifier = path.rsplit("/", 1)[1]
                profile, parse_id = extracts[identifier]
                response = {"id": identifier, "project_id": "prj-test", "status": "COMPLETED", "file_input": parse_id,
                            "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z",
                            "extract_result": {"lld": lld_evidence, "application": application_evidence, "invoice": invoice_evidence, "valas_declaration_2": valas2_evidence, "valas_declaration_1": valas1_evidence, "ektp": ektp_evidence}[profile]()}
            else:
                raise AssertionError(f"Unexpected SDK request: {request.method} {path}")
            return httpx.Response(200, json=response)
        def client(**kwargs):
            return LlamaCloud(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        env = self.root / ".env"
        env.write_text("LLAMA_CLOUD_API_KEY=synthetic-test-key\nLLAMA_CLOUD_PROJECT_ID=\nLLAMA_CLOUD_ORGANIZATION_ID=\nLLAMA_CLOUD_BASE_URL=\n")
        with patch.object(run, "LlamaCloud", side_effect=client):
            code = run.main(["--batch", "--samples-dir", str(self.samples), "--env-file", str(env), "--output", str(self.output)])
        self.assertEqual(code, 0)
        self.assertEqual((len(uploads), len(parses), len(extracts)), (6, 6, 6))
        self.assertEqual(sum(method == "POST" for method, _ in requests), 18)
        self.assertEqual([row["document_type"] for row in grouped_rows(self.output)], ["lld", "application", "invoice", "valas_declaration_2", "valas_declaration_1", "ektp"])

    def test_invoice_suffix_grouped_and_individual_exports(self):
        self.files("customer_INVOICE.PDF", "customer_transaction.pdf")
        self.assertEqual(batch.process_batch(self.args(), self.replay_document), 0)
        rows = grouped_rows(self.output)
        self.assertEqual([row["document_type"] for row in rows], ["invoice", "application"])
        self.assertEqual(rows[0]["final_total_amount"], "USD 88.00")
        self.assertEqual(rows[0]["bank_account_number"], "000123456789")
        with (self.output / rows[0]["output_directory"] / "result.csv").open(encoding="utf-8-sig", newline="") as f:
            self.assertEqual(len(next(csv.reader(f))), 19)
        self.assertNotIn("invoice_number", rows[1])
        self.assertEqual(len(rows[0]), 27)

    def test_duplicate_invoice_numbers_mark_both_documents_without_extra_jobs(self):
        self.files("copy1_invoice.pdf", "copy2_invoice.pdf")
        calls = []
        def process(argv):
            calls.append(argv)
            return self.replay_document(argv)
        self.assertEqual(batch.process_batch(self.args(), process), 0)
        self.assertEqual(len(calls), 2)
        rows = grouped_rows(self.output)
        self.assertEqual([row["validation_status"] for row in rows], ["FAIL", "FAIL"])
        for row in rows:
            report = run.read(self.output / row["output_directory"] / "validation.json")
            self.assertIn("DUPLICATE_INVOICE_NUMBER_IN_BATCH", [x["code"] for x in report["fields"]["invoice_number"]["issues"]])
            self.assertEqual(len(report["batch_duplicate_sources"]), 2)

    def test_valas2_suffix_groups_multiple_files_and_preserves_the_ten_exported_cells(self):
        self.files("a_VALAS2.PDF", "b_valas2.pdf", "c_transaction.pdf")
        self.assertEqual(batch.process_batch(self.args(), self.replay_document), 0)
        rows = csv_rows(self.output / "valas_declaration_2_result.csv")
        self.assertEqual(len(rows), 2)
        self.assertEqual([row["source_file"] for row in rows], ["a_VALAS2.PDF", "b_valas2.pdf"])
        for row in rows:
            self.assertEqual(len(row), 18)
            self.assertEqual(row["document_type"], "valas_declaration_2")
            self.assertEqual(row["currency"], "USD")
            self.assertEqual(row["validation_status"], "REVIEW")
            cells = run.read(self.output / row["output_directory"] / "columns.json")
            self.assertEqual([row[key] for key in cells["keys"]], cells["row"])
            self.assertNotIn("invoice_number", row)
            self.assertNotIn("beneficiary", row)
        self.assertFalse((self.output / "combined_result.csv").exists())
        self.assertEqual(run.read(self.output / "summary.json")["document_types"]["valas_declaration_2"]["total_files"], 2)

    def test_valas2_signature_failure_is_exported_in_its_own_summary(self):
        self.files("a_valas2.pdf")
        def process(argv):
            return self.replay_document(argv, lambda raw: raw["signatory_signature"].update(handwritten=False))
        self.assertEqual(batch.process_batch(self.args(), process), 0)
        row = csv_rows(self.output / "valas_declaration_2_result.csv")[0]
        self.assertEqual(row["validation_status"], "FAIL")
        self.assertIn("signatory_signature", row["failed_fields"])
        self.assertEqual(row["processing_status"], "COMPLETED")

    def test_valas1_summary_groups_multiple_files_separately_from_valas2(self):
        self.files("a_VALAS1.PDF", "b_valas1.pdf", "c_valas2.pdf")
        self.assertEqual(batch.process_batch(self.args(), self.replay_document), 0)
        rows = csv_rows(self.output / "valas_declaration_1_result.csv")
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertEqual(len(row), 24)
            self.assertEqual(row["document_type"], "valas_declaration_1")
            self.assertEqual(row["validation_status"], "REVIEW")
            self.assertEqual(row["identity_number"], "0001234567890123")
            self.assertEqual(row["npwp"], "012345678901234")
            self.assertNotIn("currency", row)
            self.assertNotIn("stamp_verification", row)
            exported = run.read(self.output / row["output_directory"] / "columns.json")
            self.assertEqual([row[key] for key in exported["keys"]], exported["row"])
        self.assertEqual(len(csv_rows(self.output / "valas_declaration_2_result.csv")), 1)
        summary = run.read(self.output / "summary.json")
        self.assertEqual(summary["document_types"]["valas_declaration_1"]["total_files"], 2)
        self.assertFalse((self.output / "combined_result.csv").exists())

    def test_valas1_bad_amount_fails_validation_but_exports_and_continues_batch(self):
        self.files("a_valas1.pdf", "b_valas1.pdf")
        def process(argv):
            if Path(argv[argv.index("--pdf") + 1]).name == "a_valas1.pdf":
                return self.replay_document(argv, lambda raw: raw["usage_amount"].update(amount_raw="0"))
            return self.replay_document(argv)
        self.assertEqual(batch.process_batch(self.args(), process), 0)
        rows = csv_rows(self.output / "valas_declaration_1_result.csv")
        self.assertEqual([row["processing_status"] for row in rows], ["COMPLETED", "COMPLETED"])
        self.assertEqual([row["validation_status"] for row in rows], ["FAIL", "REVIEW"])
        self.assertIn("usage_amount", rows[0]["failed_fields"])

    def test_ektp_summary_groups_multiple_cards_and_preserves_twenty_exported_cells(self):
        self.files("a_EKTP.PDF", "b_ektp.pdf", "c_valas1.pdf")
        self.assertEqual(batch.process_batch(self.args(), self.replay_document), 0)
        rows = csv_rows(self.output / "ektp_result.csv")
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertEqual(len(row), 28)
            self.assertEqual(row["document_type"], "ektp")
            self.assertEqual(row["nik"], "0001234567890123")
            self.assertEqual((row["rt"], row["rw"]), ("004", "012"))
            self.assertEqual(row["validation_status"], "REVIEW")
            self.assertNotIn("usage_amount", row)
            cells = run.read(self.output / row["output_directory"] / "columns.json")
            self.assertEqual([row[key] for key in cells["keys"]], cells["row"])
        self.assertEqual(len(csv_rows(self.output / "valas_declaration_1_result.csv")), 1)
        self.assertFalse((self.output / "combined_result.csv").exists())
        self.assertEqual(run.read(self.output / "summary.json")["document_types"]["ektp"]["total_files"], 2)

    def test_ektp_missing_photo_fails_validation_but_exports_and_continues(self):
        self.files("a_ektp.pdf", "b_ektp.pdf")
        def process(argv):
            if Path(argv[argv.index("--pdf") + 1]).name == "a_ektp.pdf":
                return self.replay_document(argv, lambda raw: raw["owner_photo"].update(present=False))
            return self.replay_document(argv)
        self.assertEqual(batch.process_batch(self.args(), process), 0)
        rows = csv_rows(self.output / "ektp_result.csv")
        self.assertEqual([row["processing_status"] for row in rows], ["COMPLETED", "COMPLETED"])
        self.assertEqual([row["validation_status"] for row in rows], ["FAIL", "REVIEW"])
        self.assertIn("owner_photo", rows[0]["failed_fields"])

    def test_no_matching_files_does_not_create_an_output(self):
        self.files("invoice.pdf")
        with self.assertRaisesRegex(ValueError, "No .*_lld.pdf"):
            batch.process_batch(self.args(), self.replay_document)
        self.assertFalse(self.output.exists())

    def test_existing_nonempty_output_is_not_overwritten(self):
        self.files("poko_lld.pdf")
        self.output.mkdir()
        marker = self.output / "keep.txt"
        marker.write_text("existing results")
        with self.assertRaisesRegex(ValueError, "new or empty"):
            batch.process_batch(self.args(), self.replay_document)
        self.assertEqual(marker.read_text(), "existing results")


if __name__ == "__main__":
    unittest.main()
