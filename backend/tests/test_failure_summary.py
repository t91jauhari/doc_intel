from app.db import Document, SessionLocal


def test_failure_summary_groups_errors_and_requires_auth(client, signed):
    # Unauthenticated access is rejected (clear the session cookie first).
    signed.cookies.clear()
    assert client.get("/api/documents/failure-summary").status_code in (401, 403)
    login = signed.post(
        "/api/auth/login",
        json={
            "organization": "sqe",
            "email": "sqe@bic.local",
            "password": "P@ssw0rd2026",
        },
    )
    assert login.status_code == 200
    signed.headers["X-CSRF-Token"] = login.json()["csrf"]
    branch = signed.get("/api/branches").json()[0]["id"]
    with SessionLocal.begin() as db:
        for i in range(3):
            db.add(
                Document(
                    org="sqe",
                    branch_id=branch,
                    case_id=f"fail-case-{i}",
                    batch_id="b",
                    filename=f"f{i}.pdf",
                    sha256=f"hash-{i}",
                    status="ERROR",
                    error="ConnectionError: network request interrupted while calling provider",
                )
            )
        db.add(
            Document(
                org="sqe",
                branch_id=branch,
                case_id="fail-case-other",
                batch_id="b",
                filename="other.pdf",
                sha256="hash-other",
                status="ERROR",
                error="Extraction returned no values",
            )
        )
        db.add(
            Document(
                org="other",
                branch_id=branch,
                case_id="foreign-case",
                batch_id="b",
                filename="foreign.pdf",
                sha256="hash-foreign",
                status="ERROR",
                error="ConnectionError: network request interrupted while calling provider",
            )
        )
    groups = signed.get("/api/documents/failure-summary?since=0").json()
    network = [g for g in groups if g["error_prefix"].startswith("ConnectionError")]
    assert len(network) == 1, groups
    entry = network[0]
    # Only org-scoped documents are counted (the 'other' org doc is excluded).
    assert entry["count"] == 3
    assert set(entry["case_ids"]) == {"fail-case-0", "fail-case-1", "fail-case-2"}
    assert entry["first_seen"] > 0
    # The unrelated error forms its own group.
    assert any(g["error_prefix"].startswith("Extraction") for g in groups)
    # A 'since' filter in the future excludes everything.
    import time

    future = signed.get(
        f"/api/documents/failure-summary?since={time.time() + 3600}"
    ).json()
    assert future == []