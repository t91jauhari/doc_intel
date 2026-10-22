"""Exercise real bundled data with the Windows CP1252 default encoding."""

from pathlib import Path

import pytest
from app.domain import ENGINE, default_config, validate_config
from app.provider import fixture_response
from app.sop import DATA, catalog


@pytest.fixture
def windows_text_default(monkeypatch):
    original = Path.read_text

    def read_text(self, encoding=None, errors=None):
        return original(self, encoding=encoding or "cp1252", errors=errors)

    monkeypatch.setattr(Path, "read_text", read_text)


def test_scope_reproduces_reported_windows_error():
    data = (DATA / "scope.json").read_bytes()
    # This is the exact offending character in the shipped v0.2 catalog.
    assert data[12675] == 0x9D
    with pytest.raises(UnicodeDecodeError):
        data.decode("cp1252")
    assert "\u201d" in data.decode("utf-8")


def test_configuration_and_all_fixtures_under_windows_default(windows_text_default):
    cfg = default_config()
    validate_config(cfg)
    for path in DATA.glob("*.json"):
        assert catalog(path.stem)
    for profile in cfg["profiles"]:
        assert fixture_response(profile)
    # The name directory uses non-ASCII text; compare semantic data, not mojibake.
    import json

    assert cfg["name_directory"] == json.loads(
        (ENGINE / "name_directory.json").read_bytes().decode("utf-8")
    )


def test_user_actions_under_windows_default(signed, windows_text_default):
    from test_platform import process_all, publish_fixture, upload

    assert signed.get("/api/config/catalog").status_code == 200
    assert signed.get("/api/config/export").status_code == 200
    publish_fixture(signed)
    result = upload(signed)
    assert result.status_code == 202, result.text
    process_all()
    detail = signed.get("/api/cases/" + result.json()["case_ids"][0]).json()
    assert all(d["status"] == "COMPLETED" for d in detail["documents"])
    assert detail["reports"]
    assert signed.get("/api/inbox").status_code == 200
