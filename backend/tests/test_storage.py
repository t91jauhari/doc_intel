import io
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from app.reporting import report_key
from app.storage import ObjectStore, object_key, original_key


def test_minio_private_roundtrip_and_connection_cleanup():
    client = Mock()
    client.bucket_exists.return_value = True
    response = Mock()
    response.read.return_value = b"%PDF-private"
    client.get_object.return_value = response
    backend = ObjectStore(client)
    key = object_key("sqe", "branch-1", "documents", "doc-1", "original.pdf")
    backend.put(key, b"%PDF-private", "application/pdf")
    args, kwargs = client.put_object.call_args
    assert args[:2] == ("sqe-documents", key)
    assert isinstance(args[2], io.BytesIO) and args[2].getvalue() == b"%PDF-private"
    assert args[3] == 12 and kwargs["content_type"] == "application/pdf"
    assert backend.read(key) == b"%PDF-private"
    response.close.assert_called_once()
    response.release_conn.assert_called_once()
    backend.delete(key)
    client.remove_object.assert_called_once_with("sqe-documents", key)
    client.set_bucket_policy.assert_not_called()


def test_minio_connection_returned_on_read_failure():
    client = Mock()
    client.bucket_exists.return_value = True
    response = client.get_object.return_value
    response.read.side_effect = IOError("interrupted")
    with pytest.raises(IOError):
        ObjectStore(client).read("sqe/branch/documents/doc/original.pdf")
    response.close.assert_called_once()
    response.release_conn.assert_called_once()


def test_keys_isolate_tenants_branches_and_report_state():
    d = SimpleNamespace(org="sqe", branch_id="a", id="1")
    before = original_key(d)
    d.branch_id = "b"
    assert original_key(d) != before
    d.org = "other"
    assert original_key(d).startswith("other/b/")
    d.state = "DRAFT"
    draft = report_key(d, "pdf")
    d.state = "FINAL"
    assert report_key(d, "pdf") != draft
    with pytest.raises(ValueError):
        object_key("../sqe", "a", "documents", "1", "original.pdf")


def test_development_bucket_bootstrap_once():
    client = Mock()
    client.bucket_exists.return_value = False
    backend = ObjectStore(client)
    backend.put("key", b"one", "application/json")
    backend.put("key2", b"two", "application/json")
    client.make_bucket.assert_called_once_with("sqe-documents")


def test_api_worker_and_report_roundtrip_through_minio_adapter(signed, monkeypatch):
    from app.storage import store
    from test_platform import uploaded_pdf, process_all, publish_fixture, upload

    objects = {}
    client = Mock()
    client.bucket_exists.return_value = True
    client.put_object.side_effect = lambda bucket, key, stream, length, **kw: (
        objects.__setitem__(key, stream.read())
    )

    def read(bucket, key):
        response = Mock()
        response.read.return_value = objects[key]
        return response

    client.get_object.side_effect = read
    backend = store()
    monkeypatch.setattr(backend, "client", client)
    monkeypatch.setattr(backend, "ready", False)
    publish_fixture(signed)
    response = upload(signed, names=("minio_ektp.pdf",), template="custom")
    assert response.status_code == 202
    case_id = response.json()["case_ids"][0]
    process_all()
    detail = signed.get("/api/cases/" + case_id).json()
    doc_id = detail["documents"][0]["id"]
    assert signed.get("/api/documents/" + doc_id + "/file").content == uploaded_pdf("minio_ektp.pdf")
    assert any(key.endswith("draft.pdf") for key in objects)
    assert any(key.endswith("draft.xlsx") for key in objects)
    assert any(key.endswith("draft.json") for key in objects)
    report_id = detail["reports"][0]["id"]
    assert signed.get("/api/reports/" + report_id + "/download").content.startswith(
        b"%PDF-"
    )
    client.set_bucket_policy.assert_not_called()


def test_report_storage_outage_preserves_visible_processing_error(signed, monkeypatch):
    from app.storage import store
    from test_platform import process_all, publish_fixture, upload
    from urllib3.exceptions import HTTPError

    backend = store()
    original_put = backend.put

    def put(key, data, mime):
        if "/reports/" in key:
            raise HTTPError("synthetic unavailable MinIO")
        return original_put(key, data, mime)

    monkeypatch.setattr(backend, "put", put)
    publish_fixture(signed)
    case_id = upload(signed, names=("outage_ektp.pdf",), template="custom").json()[
        "case_ids"
    ][0]
    import pytest

    with pytest.raises(HTTPError):
        process_all()
    detail = signed.get("/api/cases/" + case_id).json()
    assert detail["status"] == "SOP_ERROR"
    assert detail["documents"][0]["status"] == "COMPLETED"
    assert not detail["reports"]
    assert detail["sop_runs"][0]["status"] == "ERROR"
    monkeypatch.setattr(backend, "put", original_put)
    assert signed.post("/api/cases/" + case_id + "/sop-rerun").status_code == 202
    process_all()
    detail = signed.get("/api/cases/" + case_id).json()
    assert detail["reports"] and detail["documents"][0]["status"] == "COMPLETED"
