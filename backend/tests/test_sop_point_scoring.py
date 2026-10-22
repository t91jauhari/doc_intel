from app.sop_scoring import normalize_findings, point_summary

def finding(rule, result="REVIEW", **values):
    return {"rule_id": rule, "result": result, "message": "Check", "eligible": True, **values}

def test_shared_contract_and_pending_denominator():
    rules = [{"id": "text", "operator": "match_exact"}, {"id": "visual", "operator": "stamp_present"}]
    findings = normalize_findings([finding("text"), finding("visual"), finding("pass", "PASS"), finding("na", "NOT_APPLICABLE")], rules)
    assert findings[0]["result"] == "FAIL"
    assert findings[0]["reason_code"] == "INSUFFICIENT_OR_UNVERIFIED_DATA"
    assert findings[1]["result"] == "REVIEW"
    points = point_summary(findings)
    assert (points["earned"], points["possible"], points["pending"], points["failed"]) == (1, 3, 1, 1)
    assert points["percentage"] == 33.33 and points["provisional"]
    findings[1]["result"] = "PASS"  # Audited visual resolution.
    assert point_summary(findings)["earned"] == 2
    assert not point_summary(findings)["provisional"]

def test_account_and_custom_family_rule_types():
    rules = [
        {"id": "signature", "operator": "account_check", "path": "form.customer_signature", "comparison_policy": '{"kind":"manual"}'},
        {"id": "policy", "operator": "account_check", "path": "form.customer_name", "comparison_policy": '{"kind":"manual"}'},
    ]
    result = normalize_findings([finding("signature"), finding("policy")], rules)
    assert [f["result"] for f in result] == ["REVIEW", "FAIL"]
    assert point_summary([])["percentage"] is None

def test_no_document_does_not_silently_exclude_rule():
    from app.sop import evaluate
    rule = {"id":"missing", "enabled":True, "path":"invoice.amount", "operator":"required", "condition_operator":"always", "source_ref":"test", "scope_basis":"test", "report_category":"DATA_COMPLETION", "severity":"REVIEW"}
    result = evaluate([], {"sop_rules":[rule]}, {})
    assert result[0]["result"] == "FAIL"
    assert point_summary(result)["possible"] == 1
