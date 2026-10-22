import pytest

from app.configuration.field_options import text_field_options, validate_text_binding
from app.configuration.identity import IdentityBinding
from app.configuration.comparison import ComparisonPolicy


def payload():
    return {"document_families": {"custom": {"label": "Custom", "profiles": ["custom_profile"]}},
            "profiles": {"custom_profile": {"label": "Custom form", "columns": [["holder", "Holder name"]],
                "schema": {"type": "object", "properties": {
                    "holder": {"type": "object", "properties": {"raw": {"type": ["string", "null"]}, "complete": {"type": "boolean"}}},
                    "nested": {"type": "object", "properties": {"name": {"type": "string"}}},
                    "count": {"type": "integer"}, "items": {"type": "array", "items": {"type": "string"}},
                    "signature": {"type": "object", "properties": {"present": {"type": "boolean"}, "evidence": {"type": "string"}}},
                }}}}}


def test_options_follow_custom_schema_and_unwrap_text():
    result = text_field_options(payload(), "custom")
    assert [item["path"] for item in result] == ["custom_profile.holder", "custom_profile.nested.name"]
    assert result[0]["schema_path"] == "custom_profile.holder.raw"
    assert result[0]["label"] == "Holder name"


def test_unknown_family_rejected():
    with pytest.raises(ValueError, match="Unknown document family"):
        text_field_options(payload(), "absent")


def test_same_field_cannot_verify_itself():
    with pytest.raises(ValueError, match="two different fields"):
        ComparisonPolicy(left="custom.name", right="custom.name")


def test_visual_observation_cannot_be_used_as_text_evidence():
    with pytest.raises(ValueError, match="Visual-region"):
        validate_text_binding(IdentityBinding(profile="custom_profile", field_path="signature.evidence"), payload()["profiles"])
