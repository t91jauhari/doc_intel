import copy

import pytest

from app.configuration.compatibility import missing_settings, propose_compatibility, release_definition
from app.configuration.service import StaleConfiguration, preview_compatibility_upgrade
from app.domain import default_config, validate_config


def legacy():
    payload = default_config()
    for key in release_definition()["defaults"]:
        payload.pop(key)
    return payload


def test_missing_only_proposal_preserves_source_and_disables_bypass():
    payload = legacy()
    before = copy.deepcopy(payload)
    keys = [entry["key"] for entry in missing_settings(payload)["additions"]]
    proposal = propose_compatibility(payload, keys)
    assert payload == before
    assert proposal["payload"]["sop_review_bypass"] is False
    assert proposal["activated"] is False
    assert set(proposal["payload"]) - set(payload) == set(keys)
    assert {key: value for key, value in proposal["payload"].items() if key not in keys} == payload
    assert missing_settings(proposal["payload"])["additions"] == []


def test_existing_admin_settings_cannot_be_overwritten():
    with pytest.raises(ValueError, match="replace existing"):
        propose_compatibility(default_config(), ["sop_review_bypass"])


def test_filename_grouping_and_profiles_are_preserved():
    from app.grouping import plan_grouping

    payload = legacy()
    keys = [entry["key"] for entry in missing_settings(payload)["additions"]]
    draft = propose_compatibility(payload, keys)["payload"]
    names = ["account opening Alex Example_ektp.pdf", "Alex Example_riplay.pdf", "Other Customer_invoice.pdf"]
    assert plan_grouping(names, payload) == plan_grouping(names, draft)
    assert draft["profiles"] == payload["profiles"]


@pytest.mark.parametrize("keys", [[], ["unknown"], ["sop_review_bypass", "sop_review_bypass"]])
def test_invalid_selection_rejected(keys):
    with pytest.raises(ValueError):
        propose_compatibility(legacy(), keys)


def test_stale_version_rejected():
    with pytest.raises(StaleConfiguration):
        preview_compatibility_upgrade(current_version=2, expected_version=1,
                                      payload=legacy(), selected_keys=["sop_review_bypass"])


@pytest.mark.parametrize("key", ["sop_review_bypass", "sequential_page_extraction", "cross_page_reference"])
@pytest.mark.parametrize("value", [0, 1])
def test_boolean_flags_reject_integer_lookalikes(key, value):
    payload = default_config()
    payload[key] = value
    with pytest.raises(ValueError, match="true or false"):
        validate_config(payload)
