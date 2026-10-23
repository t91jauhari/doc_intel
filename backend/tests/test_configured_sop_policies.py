import copy
import pytest

from app.configuration.generic_sop import validate_generic_rules
from app.configuration.sop_policies import (
    DatePolicy,
    MoneyPolicy,
    VisualPolicy,
    evaluate_policy,
)
from app.sop import evaluate
from app.sop_scoring import point_summary
from app.transaction_flows import scope_configuration


def docs(**values):
    return [
        {
            "id": "synthetic",
            "doc_type": "form",
            "status": "COMPLETED",
            "normalized": values,
        }
    ]


def region(**patch):
    return {
        "present": True,
        "complete": True,
        "page_number": 1,
        "evidence": "Visible handwritten mark",
        **patch,
    }


@pytest.mark.parametrize(
    "patch,status",
    [
        ({}, "PASS"),
        ({"present": False}, "FAIL"),
        ({"complete": None}, "REVIEW"),
        ({"page_number": True}, "REVIEW"),
        ({"evidence": ""}, "REVIEW"),
    ],
)
def test_visual_presence_requires_grounded_observations(patch, status):
    policy = VisualPolicy(
        type="visual", check="presence", left="form.sign", right="form.sign"
    )
    assert evaluate_policy(policy, docs(sign=region(**patch)))[0] == status


def test_signature_presence_cannot_pass_consistency_and_documents_are_unambiguous():
    policy = VisualPolicy(
        type="visual", check="consistency", left="form.first", right="form.second"
    )
    assert evaluate_policy(policy, docs(first=region(), second=region()))[0] == "REVIEW"
    assert evaluate_policy(policy, [])[0] == "FAIL"
    assert (
        evaluate_policy(policy, docs(first=region(), second=region()) * 2)[1]
        == "AMBIGUOUS_DOCUMENT"
    )


def test_every_page_is_required_and_duplicate_page_numbers_do_not_pass():
    policy = VisualPolicy(
        type="visual",
        check="all_pages",
        left="form.marks",
        right="form.marks",
        expected_pages=2,
    )
    page = {
        "page_number": 1,
        "footer_present": True,
        "non_text": True,
        "complete": True,
        "evidence": "Footer ink",
    }
    marks = {"page_count": 2, "pages": [page, {**page, "page_number": 2}]}
    assert evaluate_policy(policy, docs(marks=marks))[0] == "PASS"
    marks["pages"][1]["page_number"] = 1
    assert evaluate_policy(policy, docs(marks=marks))[0] == "REVIEW"
    marks["page_count"] = 3
    assert evaluate_policy(policy, docs(marks=marks))[1] == "PAGE_COUNT_MISMATCH"


@pytest.mark.parametrize(
    "left,right,status",
    [
        ("10-09-2025", "2025-09-10", "PASS"),
        ("31-02-2025", "28-02-2025", "FAIL"),
        (None, "10-09-2025", "FAIL"),
    ],
)
def test_date_policy_does_not_infer_missing_or_impossible_dates(left, right, status):
    policy = DatePolicy(type="date", left="form.first", right="form.second")
    assert evaluate_policy(policy, docs(first=left, second=right))[0] == status


@pytest.mark.parametrize(
    "amount,currency,status",
    [
        ("1.234,56", "USD", "PASS"),
        ("1.234,57", "USD", "FAIL"),
        ("1.234,56", "EUR", "FAIL"),
        ("1.23,56", "USD", "FAIL"),
        ("0", "USD", "FAIL"),
        ("1.234,56", "ZZZ", "FAIL"),
    ],
)
def test_money_comparison_checks_separators_positive_amounts_and_currency(
    amount, currency, status
):
    policy = MoneyPolicy(
        type="money",
        left="form.first",
        right="form.second",
        left_currency="form.ccy1",
        right_currency="form.ccy2",
        decimal_separator=",",
        thousands_separator=".",
    )
    original = docs(first="1.234,56", second=amount, ccy1="USD", ccy2=currency)
    before = copy.deepcopy(original)
    assert evaluate_policy(policy, original)[0] == status
    assert original == before


def configured():
    visual = {
        "type": "object",
        "properties": {"present": {"type": "boolean"}, "complete": {"type": "boolean"}},
    }
    return {
        "family_catalog_mode": "explicit",
        "profiles": {
            "form": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "first": visual,
                        "second": visual,
                        "text": {"type": "string"},
                    },
                }
            }
        },
        "document_families": {"custom": {"label": "Custom", "profiles": ["form"]}},
        "templates": {
            "custom": {
                "label": "Custom",
                "document_family": "custom",
                "sop_rule_ids": ["visual"],
            }
        },
        "sop_rules": [],
        "generic_sop_rules": [
            {
                "id": "visual",
                "label": "Compare signing regions",
                "families": ["custom"],
                "policy": {
                    "type": "visual",
                    "check": "consistency",
                    "left": "form.first",
                    "right": "form.second",
                },
            }
        ],
    }


def test_custom_family_visual_dispatch_keeps_pending_review_in_denominator():
    cfg = configured()
    validate_generic_rules(cfg)
    result = evaluate(
        docs(first=region(), second=region()), scope_configuration(cfg, "custom"), {}
    )
    assert result[0]["result"] == "REVIEW"
    assert result[0]["evaluation_type"] == "VISUAL"
    assert result[0]["evidence"]["document_ids"] == ["synthetic"]
    assert point_summary(result) == {
        "version": 1,
        "earned": 0,
        "possible": 1,
        "passed": 0,
        "failed": 0,
        "pending": 1,
        "resolved": 0,
        "not_applicable": 0,
        "percentage": 0.0,
        "provisional": True,
    }
    cfg["generic_sop_rules"][0]["policy"]["left"] = "form.text"
    with pytest.raises(ValueError, match="region"):
        validate_generic_rules(cfg)


def test_visual_fields_are_not_exposed_as_text_or_money_fields():
    from app.configuration.field_options import policy_field_options, text_field_options

    cfg = configured()
    options = policy_field_options(cfg, "custom")
    assert {v["path"] for v in options["visual_fields"]} == {
        "form.first",
        "form.second",
    }
    assert {v["path"] for v in options["amount_fields"]} == {"form.text"}
    assert {v["path"] for v in text_field_options(cfg, "custom")} == {"form.text"}


def test_custom_visual_region_names_are_discovered_without_name_heuristics():
    from app.evidence import visual_fields

    raw = {"region_a": region(), "notes": {"raw": "Entered text", "complete": True}}
    assert [path for path, _ in visual_fields(raw)] == ["region_a"]


def test_report_group_policy_does_not_change_rule_points():
    from app.configuration.scoring import ScoreGroups, category_scores, defaults

    rules = [
        {"result": "PASS", "category": category, "eligible": True}
        for category in defaults()["forex"]["total_a"] + defaults()["forex"]["total_b"]
    ]
    groups = ScoreGroups.model_validate(defaults()["forex"])
    rules[0]["result"] = "FAIL"
    assert category_scores(rules, groups)["total_a"] == 0
    assert point_summary(rules)["earned"] == 3
    with pytest.raises(ValueError, match="once"):
        ScoreGroups(total_a=["DATA_COMPLETION"], total_b=["DATA_COMPLETION"])


def test_visual_review_requires_both_regions_and_preserves_audited_result(
    signed, monkeypatch
):
    from test_custom_profiles import configured as custom_configuration
    from test_platform import upload, process_all

    current = signed.get("/api/config").json()
    cfg = custom_configuration(current["payload"])
    profile = cfg["profiles"]["custom_note"]
    schema = {
        "type": "object",
        "description": "Source signing region",
        "properties": {
            "present": {"type": "boolean"},
            "complete": {"type": "boolean"},
            "page_number": {"type": "integer"},
            "evidence": {"type": "string"},
        },
    }
    for key in ("first", "second"):
        profile["schema"]["properties"][key] = copy.deepcopy(schema)
        profile["columns"].append([key, key.title() + " signature"])
    cfg["generic_sop_rules"].append(
        {
            "id": "custom_visual",
            "label": "Inspect both signing regions",
            "families": ["custom"],
            "policy": {
                "type": "visual",
                "check": "consistency",
                "left": "custom_note.first",
                "right": "custom_note.second",
            },
        }
    )
    cfg["templates"]["custom"]["sop_rule_ids"] = ["custom_visual"]
    if "rule_order" in cfg:
        cfg["rule_order"].append("custom_visual")
    cfg["maker_checker"] = False
    saved = signed.post(
        "/api/config/publish",
        json={"expected_version": current["version"], "payload": cfg},
    )
    assert saved.status_code == 200, saved.text
    monkeypatch.setattr(
        "app.processor.run_provider",
        lambda *args: (
            {
                "extract_result": {
                    "name": "Example",
                    "confirmation": "Example",
                    "first": region(),
                    "second": region(),
                }
            },
            {"type": "custom_note", "method": "synthetic", "confirmed": True},
        ),
    )
    uploaded = upload(
        signed,
        names=("Synthetic_customnote.pdf",),
        template="custom",
        key="visual-review",
    )
    assert uploaded.status_code == 202, uploaded.text
    process_all()
    case_id = uploaded.json()["case_ids"][0]
    case = signed.get("/api/cases/" + case_id).json()
    doc_id = case["documents"][0]["id"]
    finding = next(
        f
        for f in case["reports"][0]["snapshot"]["findings"]
        if f["rule_id"] == "custom_visual"
    )
    assert finding["result"] == "REVIEW" and finding["evaluation_type"] == "VISUAL"
    review = {
        "rule_id": "custom_visual",
        "result": "PASS",
        "reason": "Inspected both source signing regions",
        "observations": [
            {"document_id": doc_id, "page": 1, "region": "First signing region"}
        ],
    }
    assert (
        signed.post(f"/api/cases/{case_id}/sop-review", json=review).status_code == 422
    )
    review["observations"].append(
        {"document_id": doc_id, "page": 1, "region": "Second signing region"}
    )
    response = signed.post(f"/api/cases/{case_id}/sop-review", json=review)
    assert response.status_code == 202, response.text
    process_all()
    final = signed.get("/api/cases/" + case_id).json()["reports"][0]["snapshot"]
    observed = next(f for f in final["findings"] if f["rule_id"] == "custom_visual")
    assert observed["result"] == "PASS" and observed["automated_result"] == "REVIEW"
    assert len(observed["evidence"]["review"]["observations"]) == 2


def test_account_opening_keeps_its_six_historical_report_categories():
    from app.account_opening_sop import score

    categories = [
        "DATA_COMPLETION",
        "CUSTOMER_SIGNATURE",
        "OFFICER_REVIEW_APPROVAL",
        "DOCUMENT_COMPLETION",
        "DOCUMENT_VERIFICATION",
        "OBSERVATIONS",
    ]
    findings = [{"category": c, "result": "PASS", "eligible": True} for c in categories]
    findings[4]["result"] = "FAIL"
    result = score(findings)
    assert result["total_a"] == 1 and result["total_b"] == 0
    assert set(categories) <= set(result)


def test_unknown_applicability_never_silently_excludes_a_rule():
    cfg = configured()
    cfg["context_definitions"] = {
        "needed": {
            "label": "Needed",
            "kind": "enum",
            "options": ["YES", "NO", "UNKNOWN"],
        }
    }
    cfg["generic_sop_rules"][0]["applicability"] = {
        "context_key": "needed",
        "equals": "YES",
    }
    finding = evaluate(
        docs(first=region(), second=region()),
        scope_configuration(cfg, "custom"),
        {"needed": "unregistered"},
    )[0]
    assert (
        finding["result"] == "FAIL"
        and finding["reason_code"] == "APPLICABILITY_UNKNOWN"
    )
