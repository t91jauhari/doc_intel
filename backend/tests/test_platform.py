from types import SimpleNamespace

from app.db import Branch, Case, Config, Connector, Document, Job, SessionLocal, User
from app.processor import process_job
from app.security import verify_password
from sqlalchemy import select

PDF = b"%PDF-1.4\n% synthetic test upload; fixture mode does not inspect content\n%%EOF"


def publish_fixture(client):
    cfg = client.get("/api/config").json()
    cfg["payload"]["provider"] = "fixture"
    response = client.post(
        "/api/config/publish",
        json={"expected_version": cfg["version"], "payload": cfg["payload"]},
    )
    assert response.status_code == 200, response.text
    return response.json()


def upload(
    client,
    names=("poko_transaction.pdf", "poko_lld.pdf", "poko_invoice.pdf"),
    key="upload-1",
    template="forex",
):
    branch = client.get("/api/branches").json()[0]["id"]
    return client.post(
        "/api/uploads",
        data={"branch_id": branch, "template": template},
        # Distinct fixture documents need distinct bytes; otherwise upload hash
        # deduplication correctly collapses all files into one document.
        files=[("files", (name, PDF + b"\n% " + name.encode(), "application/pdf")) for name in names],
        headers={"Idempotency-Key": key},
    )


def process_all():
    with SessionLocal() as db:
        ids = db.scalars(select(Job.id).where(Job.status == "QUEUED")).all()
    for job_id in ids:
        process_job(job_id)
    from app.case_processing import process_case_run
    from app.db import CaseRun

    with SessionLocal() as db:
        runs = db.scalars(select(CaseRun.id).where(CaseRun.status == "QUEUED")).all()
    for run_id in runs:
        process_case_run(run_id)


def test_development_identity_and_password_hash(signed):
    me = signed.get("/api/auth/session").json()["user"]
    assert (
        me["organization"] == "sqe"
        and me["email"] == "sqe@bic.local"
        and me["role"] == "bank_admin"
    )
    with SessionLocal() as db:
        user = db.get(User, me["id"])
        assert user.password_hash != "P@ssw0rd2026"
        assert verify_password("P@ssw0rd2026", user.password_hash)


def test_login_rejects_wrong_credentials_and_rate_limits(client):
    for _ in range(10):
        assert (
            client.post(
                "/api/auth/login",
                json={
                    "organization": "sqe",
                    "email": "sqe@bic.local",
                    "password": "wrong",
                },
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/api/auth/login",
            json={"organization": "sqe", "email": "sqe@bic.local", "password": "wrong"},
        ).status_code
        == 429
    )


def test_auth_csrf_and_origin(signed):
    assert signed.get("/api/dashboard").status_code == 200
    assert (
        signed.post("/api/inbox/no-item/read", headers={"X-CSRF-Token": ""}).status_code
        == 403
    )
    assert (
        signed.post(
            "/api/uploads/preview",
            json={"filenames": []},
            headers={"Origin": "https://evil.example"},
        ).status_code
        == 403
    )
    assert signed.post("/api/auth/logout").status_code == 200
    assert signed.get("/api/dashboard").status_code == 401


def test_customer_labels_group_before_classification(signed):
    response = upload(
        signed,
        (
            "Forex - Poko - Aplikasi Transaksi.pdf",
            "poko_lld.pdf",
            "poko_invoice.pdf",
            "bayu_invoice.pdf",
        ),
    )
    assert response.status_code == 202, response.text
    assert len(response.json()["case_ids"]) == 2
    with SessionLocal() as db:
        cases = db.scalars(select(Case)).all()
        assert {c.customer.casefold() for c in cases} == {"poko", "bayu"}
        assert db.scalars(select(Job)).all()
        assert all(
            d.classification["method"] == "filename"
            for d in db.scalars(select(Document))
        )


def test_upload_replay_and_separate_batches_do_not_merge_names(signed):
    first = upload(signed, names=("poko_transaction.pdf",)).json()
    replay = upload(signed, names=("poko_transaction.pdf",)).json()
    second = upload(signed, names=("poko_transaction.pdf",), key="new-batch").json()
    assert first["batch_id"] == replay["batch_id"] and replay["replayed"]
    assert first["case_ids"] != second["case_ids"]


def test_invalid_pdf_is_atomic(signed):
    branch = signed.get("/api/branches").json()[0]["id"]
    response = signed.post(
        "/api/uploads",
        data={"branch_id": branch, "template": "forex"},
        files=[
            ("files", ("a_lld.pdf", PDF, "application/pdf")),
            ("files", ("b_invoice.pdf", b"not a pdf", "application/pdf")),
        ],
        headers={"Idempotency-Key": "invalid"},
    )
    assert response.status_code == 422
    with SessionLocal() as db:
        assert db.scalar(select(Document)) is None


def test_fixture_end_to_end_reports_even_when_sop_needs_review(signed):
    publish_fixture(signed)
    case_id = upload(signed).json()["case_ids"][0]
    process_all()
    detail = signed.get("/api/cases/" + case_id).json()
    assert all(d["status"] == "COMPLETED" for d in detail["documents"])
    assert detail["reports"] and detail["validation_status"] in {
        "FAIL",
        "REVIEW",
        "PASS",
    }
    assert detail["reports"][0]["snapshot"]["provider"] == "fixture"
    for fmt in ["pdf", "xlsx", "json"]:
        response = signed.get(
            "/api/reports/" + detail["reports"][0]["id"] + "/download?format=" + fmt
        )
        assert response.status_code == 200 and len(response.content) > 100
    assert signed.get("/api/inbox").json()


def test_missing_documents_generate_draft_and_action(signed):
    publish_fixture(signed)
    case_id = upload(signed, names=("poko_transaction.pdf",)).json()["case_ids"][0]
    process_all()
    case = signed.get("/api/cases/" + case_id).json()
    assert case["status"] == "WAITING_DOCUMENTS"
    assert set(case["reports"][0]["snapshot"]["missing"]) == {"lld", "invoice"}
    assert case["reports"][0]["snapshot"]["findings"]


def test_provider_not_configured_becomes_visible_error(signed):
    case_id = upload(signed, names=("poko_transaction.pdf",)).json()["case_ids"][0]
    process_all()
    case = signed.get("/api/cases/" + case_id).json()
    assert case["status"] == "PROCESSING_ERROR"
    assert "API key" in case["documents"][0]["error"]
    assert signed.get("/api/inbox").json()[0]["case_id"] == case_id


def test_config_versions_pin_existing_cases(signed):
    first = publish_fixture(signed)
    case_id = upload(signed, names=("poko_transaction.pdf",)).json()["case_ids"][0]
    cfg = signed.get("/api/config").json()
    cfg["payload"]["report_title"] = "New title"
    assert (
        signed.post(
            "/api/config/publish",
            json={"expected_version": cfg["version"], "payload": cfg["payload"]},
        ).status_code
        == 200
    )
    assert (
        signed.post(
            "/api/config/publish",
            json={"expected_version": cfg["version"], "payload": cfg["payload"]},
        ).status_code
        == 409
    )
    process_all()
    case = signed.get("/api/cases/" + case_id).json()
    assert case["config_version"] == first["version"]
    assert case["reports"][0]["snapshot"]["config_version"] == first["version"]


def test_correction_preserves_raw_and_revalidates_without_cloud(signed):
    publish_fixture(signed)
    case_id = upload(signed, names=("poko_ektp.pdf",), template="custom").json()[
        "case_ids"
    ][0]
    process_all()
    doc = signed.get("/api/cases/" + case_id).json()["documents"][0]
    response = signed.post(
        "/api/documents/" + doc["id"] + "/corrections",
        json={"field": "rt", "value": "7", "reason": "Verified from source card"},
    )
    assert response.status_code == 202, response.text
    process_all()
    updated = signed.get("/api/cases/" + case_id).json()["documents"][0]
    assert (
        updated["raw"]["rt"] == "4"
        and updated["overrides"]["rt"] == "7"
        and updated["normalized"]["rt"] == "007"
    )


def test_csvs_are_separate_and_keep_leading_zero(signed):
    publish_fixture(signed)
    upload(signed, names=("poko_ektp.pdf",), template="custom")
    process_all()
    content = signed.get("/api/exports/ektp").text
    assert "nik" in content and "0001234567890123" in content
    assert "beneficiary_bank" not in content
    assert signed.get("/api/exports/application").status_code == 200


def test_connector_key_encrypted_and_never_returned(signed):
    assert (
        signed.put(
            "/api/connector", json={"api_key": "llx-test-key-not-live"}
        ).status_code
        == 200
    )
    assert "llx-test-key-not-live" not in signed.get("/api/connector").text
    with SessionLocal() as db:
        assert "llx-test-key-not-live" not in db.scalar(select(Connector)).encrypted
    assert (
        signed.put("/api/connector", json={"api_key": "Bearer llx-test"}).status_code
        == 422
    )


def test_cross_branch_access_denied_everywhere(signed):
    publish_fixture(signed)
    case_id = upload(signed, names=("poko_ektp.pdf",), template="custom").json()[
        "case_ids"
    ][0]
    process_all()
    detail = signed.get("/api/cases/" + case_id).json()
    doc = detail["documents"][0]
    report = detail["reports"][0]
    branch = signed.post(
        "/api/branches", json={"code": "OTHER", "name": "Other branch"}
    ).json()
    assert (
        signed.post(
            "/api/users",
            json={
                "email": "other@bic.local",
                "name": "Other officer",
                "password": "AnotherPassword2026!",
                "role": "officer",
                "branches": [branch["id"]],
            },
        ).status_code
        == 200
    )
    other = signed.post(
        "/api/auth/login",
        json={
            "organization": "sqe",
            "email": "other@bic.local",
            "password": "AnotherPassword2026!",
        },
    ).json()
    signed.headers["X-CSRF-Token"] = other["csrf"]
    assert signed.get("/api/cases").json()["items"] == []
    for path in [
        "/api/cases/" + case_id,
        "/api/documents/" + doc["id"] + "/file",
        "/api/reports/" + report["id"] + "/download",
    ]:
        assert signed.get(path).status_code == 404
    assert signed.get("/api/inbox").json() == []
    assert all(
        x["case_id"] != case_id for x in signed.get("/api/events").json()["items"]
    )
    assert "poko_ektp" not in signed.get("/api/exports/ektp").text
    assert (
        signed.post(
            "/api/config/publish", json={"expected_version": 2, "payload": {}}
        ).status_code
        == 403
    )


def test_uncertain_submission_blocks_duplicate_creation(signed):
    cfg=signed.get('/api/config').json()
    cfg['payload']['provider']='llama'
    assert signed.post('/api/config/publish',json={'expected_version':cfg['version'],'payload':cfg['payload']}).status_code==200
    signed.put("/api/connector", json={"api_key": "llx-not-live"})
    case_id = upload(signed, names=("poko_transaction.pdf",)).json()["case_ids"][0]
    with SessionLocal.begin() as db:
        d = db.scalar(select(Document))
        d.provider_state = {"pending_create": "file_id"}
    process_all()
    doc = signed.get("/api/cases/" + case_id).json()["documents"][0]
    assert doc["status"] == "ERROR" and "uncertain" in doc["error"]
    assert signed.post("/api/documents/" + doc["id"] + "/retry").status_code == 409


def test_bulk_retry_requeues_all_failed_documents_in_case(signed):
    # Build a case with failed documents directly in the DB, avoiding the
    # upload/worker pipeline (which needs a configured provider).
    with SessionLocal.begin() as db:
        branch = db.scalar(select(Branch))
        config = db.scalar(select(Config).order_by(Config.version.desc()))
        user = db.scalar(select(User))
        case = Case(
            org="sqe",
            branch_id=branch.id,
            reference="BULK-RETRY-1",
            customer="Bulk Retry Customer",
            template="forex",
            created_by=user.id,
            config_id=config.id,
        )
        db.add(case)
        db.flush()
        for i in range(3):
            db.add(
                Document(
                    org="sqe",
                    branch_id=branch.id,
                    case_id=case.id,
                    batch_id="batch-bulk-retry",
                    filename=f"doc_{i}.pdf",
                    sha256=f"hash_{i}",
                    doc_type="unknown",
                    status="ERROR",
                    error="synthetic failure",
                    provider_state={},
                )
            )
        case_id = case.id
    response = signed.post("/api/cases/" + case_id + "/retry-documents")
    assert response.status_code == 202, response.text
    body = response.json()
    assert len(body["queued"]) == 3
    assert body["skipped"] == []
    # Documents are no longer in an error state after being re-queued.
    with SessionLocal() as db:
        statuses = [
            d.status
            for d in db.scalars(select(Document).where(Document.case_id == case_id))
        ]
    assert all(s != "ERROR" for s in statuses)


def test_bulk_retry_skips_uncertain_submissions(signed):
    with SessionLocal.begin() as db:
        branch = db.scalar(select(Branch))
        config = db.scalar(select(Config).order_by(Config.version.desc()))
        user = db.scalar(select(User))
        case = Case(
            org="sqe",
            branch_id=branch.id,
            reference="BULK-RETRY-2",
            customer="Bulk Retry Customer 2",
            template="forex",
            created_by=user.id,
            config_id=config.id,
        )
        db.add(case)
        db.flush()
        db.add(
            Document(
                org="sqe",
                branch_id=branch.id,
                case_id=case.id,
                batch_id="batch-bulk-retry-2",
                filename="doc_uncertain.pdf",
                sha256="hash_uncertain",
                doc_type="unknown",
                status="ERROR",
                error="uncertain",
                provider_state={"pending_create": "file_id"},
            )
        )
        case_id = case.id
    response = signed.post("/api/cases/" + case_id + "/retry-documents")
    assert response.status_code == 202
    body = response.json()
    assert body["queued"] == []
    assert len(body["skipped"]) == 1
    assert "uncertain" in body["skipped"][0]["reason"]


def test_bulk_retry_requeues_documents_in_any_state(signed):
    # The bulk retry button is available even when no document is in an error
    # state — it re-extracts every document regardless of status. Only
    # documents with an uncertain provider submission are skipped.
    with SessionLocal.begin() as db:
        branch = db.scalar(select(Branch))
        config = db.scalar(select(Config).order_by(Config.version.desc()))
        user = db.scalar(select(User))
        case = Case(
            org="sqe",
            branch_id=branch.id,
            reference="BULK-RETRY-3",
            customer="Bulk Retry Customer 3",
            template="forex",
            created_by=user.id,
            config_id=config.id,
        )
        db.add(case)
        db.flush()
        # One completed document and one error document — both should be queued.
        for status, suffix in [("COMPLETED", "done"), ("ERROR", "err")]:
            db.add(
                Document(
                    org="sqe",
                    branch_id=branch.id,
                    case_id=case.id,
                    batch_id="batch-bulk-retry-3",
                    filename=f"doc_{suffix}.pdf",
                    sha256=f"hash_{suffix}",
                    doc_type="unknown",
                    status=status,
                    error="" if status == "COMPLETED" else "synthetic failure",
                    provider_state={},
                )
            )
        case_id = case.id
    response = signed.post("/api/cases/" + case_id + "/retry-documents")
    assert response.status_code == 202, response.text
    body = response.json()
    assert len(body["queued"]) == 2
    assert body["skipped"] == []
    # Both documents are now queued for re-extraction.
    with SessionLocal() as db:
        statuses = [
            d.status
            for d in db.scalars(select(Document).where(Document.case_id == case_id))
        ]
    assert all(s == "QUEUED" for s in statuses)



def test_classification_mismatch_stops_before_extraction(signed, monkeypatch):
    import app.provider as provider
    cfg=signed.get('/api/config').json()
    cfg['payload']['provider']='llama'
    assert signed.post('/api/config/publish',json={'expected_version':cfg['version'],'payload':cfg['payload']}).status_code==200

    called = []

    class Model:
        id = "classify-test"
        status = "COMPLETED"
        result = SimpleNamespace(
            model_dump=lambda **_: {
                "type": "invoice",
                "confidence": 0.99,
                "reasoning": "Invoice table and payment instructions",
            }
        )

    class FakeClient:
        def __init__(self, **_):
            self.files = SimpleNamespace(
                create=lambda **kw: SimpleNamespace(id="file-test")
            )
            self.classify = SimpleNamespace(
                create=lambda **kw: SimpleNamespace(id="classify-test"),
                get=lambda *a, **kw: Model(),
            )
            self.parsing = SimpleNamespace(create=lambda **kw: called.append("parse"))

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    monkeypatch.setattr(provider, "LlamaCloud", FakeClient)
    signed.put("/api/connector", json={"api_key": "llx-not-live"})
    case_id = upload(signed, names=("poko_transaction.pdf",)).json()["case_ids"][0]
    process_all()
    doc = signed.get("/api/cases/" + case_id).json()["documents"][0]
    assert doc["status"] == "NEEDS_CLASSIFICATION" and not called
    assert doc["classification"]["type"] == "invoice"


def test_read_inbox_does_not_resolve_case(signed):
    publish_fixture(signed)
    upload(signed, names=("poko_transaction.pdf",))
    process_all()
    item = signed.get("/api/inbox").json()[0]
    assert signed.post("/api/inbox/" + item["id"] + "/read").status_code == 200
    after = signed.get("/api/inbox").json()[0]
    assert after["read"] and after["id"] == item["id"]


def test_configuration_test_does_not_publish_or_modify_results(signed):
    publish_fixture(signed)
    upload(signed, names=("poko_ektp.pdf",), template="custom")
    process_all()
    cfg = signed.get("/api/config").json()
    before = signed.get("/api/reports").json()
    cfg["payload"]["profiles"]["ektp"]["policy"]["minimum_confidence"] = 0.999
    result = signed.post(
        "/api/config/test",
        json={"expected_version": cfg["version"], "payload": cfg["payload"]},
    )
    assert result.status_code == 200 and result.json()["tested"] == 1
    assert signed.get("/api/config").json()["version"] == cfg["version"]
    assert signed.get("/api/reports").json() == before


def test_failed_sop_report_cannot_be_released(signed):
    publish_fixture(signed)
    case_id = upload(signed, names=("poko_transaction.pdf",)).json()["case_ids"][0]
    process_all()
    report = signed.get("/api/cases/" + case_id).json()["reports"][0]
    assert signed.post("/api/reports/" + report["id"] + "/approve").status_code == 409


def test_classify_selects_schema_and_extract_reuses_parse_id(signed, monkeypatch):
    import app.provider as provider

    config = signed.get("/api/config").json()
    config['payload']['provider']='llama'
    instruction = "Extract the complete entered bank branch name from the labelled branch field."
    config["payload"]["profiles"]["application"]["schema"]["properties"]["branch"]["description"] = instruction
    assert signed.post("/api/config/publish", json={"expected_version": config["version"], "payload": config["payload"]}).status_code == 200

    calls = []
    response = provider.fixture_response("application")

    class FakeClient:
        def __init__(self, **_):
            def upload(**kwargs):
                calls.append("upload")
                return SimpleNamespace(id="file-test")

            def classify(**kwargs):
                calls.append("classify")
                assert kwargs["file_input"] == "file-test"
                assert {x["type"] for x in kwargs["configuration"]["rules"]} == set(
                    signed.get("/api/config").json()["payload"]["profiles"]
                )
                return SimpleNamespace(id="classify-test")

            def parse(**kwargs):
                calls.append("parse")
                assert (
                    kwargs["file_id"] == "file-test"
                    and kwargs["tier"] == "agentic_plus"
                )
                return SimpleNamespace(id="parse-test")

            def extract(**kwargs):
                calls.append("extract")
                assert kwargs["file_input"] == "parse-test"
                assert kwargs["configuration"]["tier"] == "agentic_plus"
                properties = kwargs["configuration"]["data_schema"]["properties"]
                assert len(set(properties) - {"_field_locations"}) == 23
                assert "_field_locations" in properties
                assert kwargs["configuration"]["data_schema"]["properties"]["branch"]["description"] == instruction
                assert "_visual_evidence" not in kwargs["configuration"]["data_schema"]["properties"]
                return SimpleNamespace(id="extract-test")

            self.files = SimpleNamespace(create=upload)
            self.classify = SimpleNamespace(
                create=classify,
                get=lambda *a, **kw: SimpleNamespace(
                    status="COMPLETED",
                    result=SimpleNamespace(
                        model_dump=lambda **_: {
                            "type": "application",
                            "confidence": 0.99,
                            "reasoning": "Bank transaction form",
                        }
                    ),
                ),
            )
            self.parsing = SimpleNamespace(
                create=parse,
                get=lambda *a, **kw: SimpleNamespace(
                    job=SimpleNamespace(status="COMPLETED"),
                    model_dump=lambda **_: {"job": {"id": "parse-test", "status": "COMPLETED"}, "items": {"pages": []}, "forms": {"pages": []}}
                ),
            )
            self.extract = SimpleNamespace(
                create=extract,
                get=lambda *a, **kw: SimpleNamespace(
                    status="COMPLETED", model_dump=lambda **_: response
                ),
            )

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    monkeypatch.setattr(provider, "LlamaCloud", FakeClient)
    signed.put("/api/connector", json={"api_key": "llx-not-live"})
    case_id = upload(signed, names=("poko_transaction.pdf",), template="custom").json()[
        "case_ids"
    ][0]
    process_all()
    doc = signed.get("/api/cases/" + case_id).json()["documents"][0]
    assert doc["status"] == "COMPLETED" and calls == [
        "upload",
        "classify",
        "parse",
        "extract",
    ]
    assert doc["provider_state"]["extract_job_id"] == "extract-test"
    assert (
        signed.post(
            "/api/documents/" + doc["id"] + "/corrections",
            json={
                "field": "branch",
                "value": "KCP Reviewed Branch",
                "reason": "Verified printed branch name",
            },
        ).status_code
        == 202
    )
    process_all()
    assert calls == ["upload", "classify", "parse", "extract"]
