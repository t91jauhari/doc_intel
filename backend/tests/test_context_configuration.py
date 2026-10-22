import copy
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.configuration.contexts import definitions, enum_options, default_definitions, propose_defaults, validate_values
from app.configuration.store import ConfigurationBase, ContextDefinitionRecord, import_publication, compile_publication
from test_platform import upload


def test_legacy_definitions_and_explicit_empty_are_distinct():
    assert enum_options({})["customer_type"] == ["INDIVIDUAL", "COMPANY", "UNKNOWN"]
    assert definitions({"context_definitions": {}}) == {}
    source = {}
    draft = propose_defaults(source)
    draft["context_definitions"]["customer_type"]["options"].append("SYNTHETIC")
    assert source == {} and "SYNTHETIC" not in default_definitions()["customer_type"]["options"]


@pytest.mark.parametrize("definition", [
    {"label": "Flag", "kind": "enum", "options": []},
    {"label": "Flag", "kind": "enum", "options": ["YES", "YES"]},
    {"label": "Reference", "kind": "document_reference"},
    {"label": "Text", "kind": "text", "options": ["YES"]},
])
def test_invalid_definition_rejected(definition):
    with pytest.raises(ValueError):
        definitions({"context_definitions": {"synthetic": definition}})


def test_values_and_document_references_follow_configuration():
    payload = {"context_definitions": {
        "flag": {"label": "Flag", "kind": "enum", "options": ["YES", "NO"]},
        "number": {"label": "Number", "kind": "digits", "max_length": 4},
        "reference": {"label": "Reference", "kind": "document_reference", "profiles": ["ektp"]},
    }}
    validate_values(payload, {"flag": "YES", "number": "0012"})
    for values in [{"flag": "MAYBE"}, {"number": "12345"}, {"number": "A1"}, {"missing": "x"}]:
        with pytest.raises(ValueError):
            validate_values(payload, values)
    doc = SimpleNamespace(case_id="case", doc_type="ektp", status="COMPLETED")
    validate_values(payload, {"reference": "doc"}, document_lookup=lambda _: doc, case_id="case")
    with pytest.raises(ValueError, match="this case"):
        validate_values(payload, {"reference": "doc"}, document_lookup=lambda _: doc, case_id="other")


def test_context_records_round_trip_without_extensions_duplication():
    engine = create_engine("sqlite://")
    ConfigurationBase.metadata.create_all(engine)
    payload = {"profiles": {}, "context_definitions": {"flag": {"label": "Flag", "kind": "enum", "options": ["YES", "NO"]}}}
    with Session(engine) as session, session.begin():
        publication = import_publication(session, organization="synthetic", revision=1, source_config_id="source", payload=payload)
        assert publication.extensions["context_definitions"] == {}
        assert session.scalar(select(ContextDefinitionRecord)).context_key == "flag"
        assert compile_publication(session, publication) == payload
    engine.dispose()


def test_catalog_and_case_edit_use_pinned_context_definitions(signed):
    current = signed.get("/api/config").json()
    payload = copy.deepcopy(current["payload"])
    payload["context_definitions"]["synthetic_flag"] = {"label": "Synthetic flag", "kind": "enum", "options": ["ALLOW", "UNKNOWN"]}
    response = signed.post("/api/config/publish", json={"expected_version": current["version"], "payload": payload})
    assert response.status_code == 200, response.text
    version = response.json()["version"]
    created = upload(signed, names=("Synthetic_ektp.pdf",), key="context-pin")
    assert created.status_code == 202, created.text
    case_id = created.json()["case_ids"][0]
    payload["context_definitions"]["synthetic_flag"]["options"] = ["DENY", "UNKNOWN"]
    assert signed.post("/api/config/publish", json={"expected_version": version, "payload": payload}).status_code == 200
    pinned = signed.get(f"/api/config/catalog?case_id={case_id}").json()
    assert pinned["context"]["synthetic_flag"] == ["ALLOW", "UNKNOWN"]
    assert signed.get("/api/config/catalog").json()["context"]["synthetic_flag"] == ["DENY", "UNKNOWN"]
    body = {"values": {"synthetic_flag": "ALLOW"}, "reason": "Read evidence", "evidence": "Document page 1"}
    saved = signed.put(f"/api/cases/{case_id}/context", json=body)
    assert saved.status_code == 200, saved.text
    body["values"]["synthetic_flag"] = "DENY"
    assert signed.put(f"/api/cases/{case_id}/context", json=body).status_code == 422
