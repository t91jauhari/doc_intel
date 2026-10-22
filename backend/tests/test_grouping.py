import itertools
import json
from sqlalchemy import select
from app.db import Case, Document, Job, SessionLocal
from app.domain import default_config, route
from app.grouping import identity_conflicts, plan_grouping
from test_platform import PDF, upload


def test_dirman_is_order_independent():
    names = [
        "Dirman S_lld.pdf",
        "Dirman Siswanto_transaction.pdf",
        "(invoice)- Dirman S.pdf",
    ]
    for order in itertools.permutations(names):
        rows = plan_grouping(order, default_config())
        assert {r["customer"] for r in rows} == {"Dirman"}
        assert all(r["status"] == "automatic" for r in rows)


def test_abbreviation_never_bridges_full_names():
    rows = plan_grouping(
        [
            "Dirman S_lld.pdf",
            "Dirman Siswanto_invoice.pdf",
            "Dirman Santoso_transaction.pdf",
            "Dirman_ektp.pdf",
        ],
        default_config(),
    )
    assert rows[0]["status"] == rows[3]["status"] == "unresolved"
    assert rows[0]["candidates"] == ["Dirman Santoso", "Dirman Siswanto"]
    assert {r["customer"] for r in rows[1:3]} == {"Dirman Siswanto", "Dirman Santoso"}


def test_general_names_and_missing_customer():
    rows = plan_grouping(
        [
            "SriP_lld.pdf",
            "SriPujianty_invoice.pdf",
            "LangitR_lld.pdf",
            "LangitRaharja_transaction.pdf",
            "invoice.pdf",
            "scan_001.pdf",
        ],
        default_config(),
    )
    assert [r["customer"] for r in rows[:4]] == ["Sri", "Sri", "Langit", "Langit"]
    assert all(r["status"] == "unresolved" for r in rows[4:])


def test_punctuation_and_unicode_names():
    rows = plan_grouping(
        [
            "José S_lld.pdf",
            "José Silva_invoice.pdf",
            "SITI__AMINAH_lld.pdf",
            "siti aminah_invoice.pdf",
        ],
        default_config(),
    )
    assert rows[0]["customer"] == rows[1]["customer"] == "José"
    assert rows[2]["customer"] == rows[3]["customer"]


def test_preview_and_upload_use_same_plan(signed):
    names = [
        "Dirman S_lld.pdf",
        "Dirman Siswanto_transaction.pdf",
        "(invoice)- Dirman S.pdf",
    ]
    preview = signed.post("/api/uploads/preview", json={"filenames": names}).json()
    assert {r["customer"] for r in preview} == {"Dirman"}
    response = upload(signed, names=names)
    assert response.status_code == 202, response.text
    assert len(response.json()["case_ids"]) == 1
    with SessionLocal() as db:
        assert db.scalar(select(Case)).customer == "Dirman"
        documents = db.scalars(select(Document)).all()
        # upload() creates distinct bytes for each fixture filename.
        assert len(documents) == len(names)
        assert {doc.filename for doc in documents} == set(names)
        assert all(doc.provider_state["grouping"]["original_customer"] for doc in documents)


def test_unresolved_upload_is_atomic_and_manual_assignment_works(signed):
    names = [
        "Dirman S_lld.pdf",
        "Dirman Siswanto_invoice.pdf",
        "Dirman Santoso_transaction.pdf",
    ]
    response = upload(signed, names=names)
    assert response.status_code == 422
    with SessionLocal() as db:
        assert not db.scalars(select(Case)).all()
        assert not db.scalars(select(Job)).all()
    branch = signed.get("/api/branches").json()[0]["id"]
    response = signed.post(
        "/api/uploads",
        data={
            "branch_id": branch,
            "template": "forex",
            "grouping": json.dumps({names[0]: "Dirman Siswanto"}),
        },
        files=[
            ("files", (name, PDF + str(i).encode(), "application/pdf"))
            for i, name in enumerate(names)
        ],
        headers={"Idempotency-Key": "manual"},
    )
    assert response.status_code == 202, response.text
    with SessionLocal() as db:
        cases = db.scalars(select(Case)).all()
        assert len(cases) == 2
        target = next(c for c in cases if c.customer == "Dirman Siswanto")
        assert (
            len(db.scalars(select(Document).where(Document.case_id == target.id)).all())
            == 2
        )


def test_identical_content_is_deduplicated_independently_of_filename(signed):
    branch = signed.get("/api/branches").json()[0]["id"]
    response = signed.post("/api/uploads", data={"branch_id": branch, "template": "forex"},
        files=[("files", (name, PDF, "application/pdf")) for name in
               ("Synthetic_ektp.pdf", "Synthetic_lld.pdf", "Synthetic_invoice.pdf")],
        headers={"Idempotency-Key": "identical-content"})
    assert response.status_code == 202, response.text
    with SessionLocal() as db:
        assert len(db.scalars(select(Document)).all()) == 1
        assert len(db.scalars(select(Job)).all()) == 1
        assert len(db.scalars(select(Case)).all()) == 1


def test_duplicate_filenames_are_rejected(signed):
    assert upload(signed, names=["Dirman_lld.pdf", "Dirman_lld.pdf"]).status_code == 422


def test_repair_existing_split_batch_preserves_documents(signed):
    branch = signed.get("/api/branches").json()[0]["id"]
    names = [
        "Dirman S_lld.pdf",
        "Dirman Siswanto_transaction.pdf",
        "(invoice)- Dirman S.pdf",
    ]
    response = signed.post(
        "/api/uploads",
        data={
            "branch_id": branch,
            "template": "forex",
            "grouping": json.dumps(
                dict(zip(names, ["Dirman S", "Dirman Siswanto", "(Invoice)-Dirman S"]))
            ),
        },
        files=[
            ("files", (name, PDF + str(i).encode(), "application/pdf"))
            for i, name in enumerate(names)
        ],
        headers={"Idempotency-Key": "old-split"},
    )
    assert response.status_code == 202, response.text
    batch = response.json()["batch_id"]
    assert len(response.json()["case_ids"]) == 3
    preview = signed.get(f"/api/batches/{batch}/grouping").json()
    payload = dict(
        labels={r["filename"]: r["customer"] for r in preview["rows"]},
        revision=preview["revision"],
        reason="Repair old filename grouping.",
    )
    assert (
        signed.post(f"/api/batches/{batch}/grouping", json=payload).status_code == 409
    )
    with SessionLocal.begin() as db:
        for job in db.scalars(select(Job)):
            job.status = "ERROR"
        for doc in db.scalars(select(Document)):
            doc.status = "ERROR"
            doc.raw = {"saved_result": doc.id}
    preview = signed.get(f"/api/batches/{batch}/grouping").json()
    payload["revision"] = preview["revision"]
    result = signed.post(f"/api/batches/{batch}/grouping", json=payload)
    assert result.status_code == 200, result.text
    assert len(result.json()["case_ids"]) == 1
    with SessionLocal() as db:
        docs = db.scalars(select(Document)).all()
        assert len(docs) == 3
        assert len({d.case_id for d in docs}) == 1
        assert all(d.raw == {"saved_result": d.id} for d in docs)
        assert db.get(Case, docs[0].case_id).customer == "Dirman"
        assert len(db.scalars(select(Case).where(Case.status == "MERGED")).all()) == 2
        assert all(j.status == "ERROR" for j in db.scalars(select(Job)))
    assert len(signed.get("/api/cases").json()["items"]) == 1
    assert (
        signed.post(f"/api/batches/{batch}/grouping", json=payload).status_code == 409
    )


def test_repair_batch_authorization_and_labels(signed):
    response = upload(signed, names=["Poko_lld.pdf"])
    batch = response.json()["batch_id"]
    assert signed.get("/api/batches/not-found/grouping").status_code == 404
    preview = signed.get(f"/api/batches/{batch}/grouping").json()
    assert (
        signed.post(
            f"/api/batches/{batch}/grouping",
            json=dict(
                labels={}, revision=preview["revision"], reason="Correct grouping"
            ),
        ).status_code
        == 422
    )


def test_similar_spellings_require_confirmation():
    rows = plan_grouping(
        ["Siti Aminah_lld.pdf", "Siti Amanah_invoice.pdf"], default_config()
    )
    assert all(r["status"] == "unresolved" for r in rows)
    assert set(rows[0]["candidates"]) == {"Siti Aminah", "Siti Amanah"}


def test_extracted_customer_conflict_excludes_invoice_supplier():
    docs = [
        dict(
            id="id1",
            doc_type="ektp",
            status="COMPLETED",
            normalized={"name": "Dirman Siswanto"},
        ),
        dict(
            id="id2",
            doc_type="application",
            status="COMPLETED",
            normalized={"remitter": {"name": "Dirman S"}},
        ),
        dict(
            id="invoice",
            doc_type="invoice",
            status="COMPLETED",
            normalized={"supplier_name": "Other Customer"},
        ),
    ]
    assert not identity_conflicts(docs)
    docs.append(
        dict(
            id="id3",
            doc_type="riplay",
            status="COMPLETED",
            normalized={"customer_name": "Dirman Santoso"},
        )
    )
    findings = identity_conflicts(docs)
    assert findings[0]["result"] == "REVIEW"
    assert "invoice" not in findings[0]["evidence"]["document_ids"]


def test_name_free_suffix_requires_assignment():
    assert plan_grouping(["_lld.pdf"], default_config())[0]["status"] == "unresolved"


def test_filename_label_variants_preserve_customer():
    cfg = default_config()
    for name, hint in [
        ("(Invoice)- Dirman S.pdf", "invoice"),
        ("[Invoice]__Dirman_S.pdf", "invoice"),
        ("Dirman S (Invoice).pdf", "invoice"),
        ("Form__LLD-Dirman Siswanto.pdf", "lld"),
        (
            "Dirman - Surat Pernyataan Pembelian Valas 1 (Diatas Jumlah Threshold).pdf",
            "valas_declaration_1",
        ),
    ]:
        actual, customer, _ = route(name, cfg)
        assert actual == hint, name
        assert customer.startswith("Dirman"), name


def test_repair_is_scoped_to_organization(signed):
    from app.db import Batch

    with SessionLocal.begin() as db:
        foreign = Batch(
            org="different-organization",
            branch_id="foreign-branch",
            created_by="other-user",
            idempotency_key="foreign-batch",
        )
        db.add(foreign)
        db.flush()
        bid = foreign.id
    assert signed.get(f"/api/batches/{bid}/grouping").status_code == 404
