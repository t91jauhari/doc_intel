import copy

import pytest

from app.domain import default_config, validate_config
from app.sop import evaluate
from app.sop_scoring import point_summary
from app.transaction_flows import scope_configuration, score_configuration


def configured():
    cfg = default_config()
    cfg["generic_sop_rules"] = [{
        "id": "configured_customer", "label": "Customer names must match",
        "families": ["forex"], "source_ref": "SOP3:custom-reference-only",
        "policy": {"left": "ektp.name", "right": "riplay.customer_name", "normalization": "casefold_whitespace"},
        "schema_paths": {"ektp.name": "ektp.name.raw", "riplay.customer_name": "riplay.customer_name.raw"},
    }]
    flow = next(iter(cfg["templates"]))
    cfg["templates"][flow].update(document_family="forex", sop_rule_ids=["configured_customer"])
    return cfg, flow


def documents():
    return [{"id": "a", "doc_type": "ektp", "status": "COMPLETED", "normalized": {"name": "Alex Example"}},
            {"id": "b", "doc_type": "riplay", "status": "COMPLETED", "normalized": {"customer_name": "alex example"}}]


def run(cfg, flow, docs=None, context=None):
    validate_config(cfg)
    scoped = scope_configuration(cfg, flow)
    return evaluate(documents() if docs is None else docs, scoped, context or {})


def test_runtime_dispatch_and_scoring():
    cfg, flow = configured()
    results = run(cfg, flow)
    assert len(results) == 1 and results[0]["result"] == "PASS"
    assert results[0]["evaluation_type"] == "DATA"
    assert results[0]["evidence"]["document_ids"] == ["a"]
    assert results[0]["evidence"]["reference_document_ids"] == ["b"]
    assert point_summary(results)["earned"] == 1
    assert score_configuration(cfg, flow, results)["DATA_COMPLETION"] == 1


def test_uncertain_sources_fail_without_visual_queue():
    cfg, flow = configured()
    docs = documents()
    docs[1]["validation"] = {"fields": {"customer_name": {"issues": [{"severity": "REVIEW"}]}}}
    result = run(cfg, flow, docs)[0]
    assert result["result"] == "FAIL"
    assert result["reason_code"] == "INSUFFICIENT_OR_UNVERIFIED_DATA"
    assert result["evaluation_type"] == "DATA"
    assert point_summary([result])["possible"] == 1


@pytest.mark.parametrize("context,status,possible", [({}, "FAIL", 1), ({"required": "NO"}, "NOT_APPLICABLE", 0), ({"required": "YES"}, "PASS", 1)])
def test_explicit_applicability(context, status, possible):
    cfg, flow = configured()
    cfg["generic_sop_rules"][0]["applicability"] = {"context_key": "required", "equals": "YES"}
    result = run(cfg, flow, context=context)
    assert result[0]["result"] == status
    assert point_summary(result)["possible"] == possible


def test_missing_and_ambiguous_documents_fail():
    cfg, flow = configured()
    assert run(cfg, flow, documents()[:1])[0]["result"] == "FAIL"
    assert run(cfg, flow, documents() + [documents()[0]])[0]["result"] == "FAIL"


def test_disabled_and_explicit_empty_selection():
    cfg, flow = configured()
    cfg["generic_sop_rules"][0]["enabled"] = False
    assert run(cfg, flow) == []
    cfg["generic_sop_rules"][0]["enabled"] = True
    cfg["templates"][flow]["sop_rule_ids"] = []
    assert run(cfg, flow) == []


def test_unsupported_field_or_duplicate_id_rejected():
    cfg, _ = configured()
    cfg["generic_sop_rules"][0]["id"] = cfg["sop_rules"][0]["id"]
    with pytest.raises(ValueError, match="unique"):
        validate_config(cfg)
    cfg, _ = configured()
    cfg["generic_sop_rules"][0]["schema_paths"]["ektp.name"] = "ektp.not_present"
    with pytest.raises(ValueError):
        validate_config(cfg)


def test_processing_does_not_mutate_configuration():
    cfg, flow = configured()
    snapshot = copy.deepcopy(cfg)
    run(cfg, flow)
    assert cfg == snapshot


def test_configured_findings_render_in_excel_report():
    import io
    from openpyxl import load_workbook
    from app.kertas_kerja import workbook
    from test_kertas_kerja_layout import sample

    cfg, flow = configured()
    docs = documents()
    docs[1]["normalized"]["customer_name"] = "Other Customer"
    for doc in docs:
        doc.update(filename="synthetic.pdf", raw={}, overrides={}, sha256="synthetic-source", validation={})
    findings = run(cfg, flow, docs)
    snapshot = sample()
    snapshot.update(configuration=cfg, template=flow, documents=docs, findings=findings,
                    scores=score_configuration(cfg, flow, findings))
    book = load_workbook(io.BytesIO(workbook([snapshot])))
    rows = list(book["SOP Details"].values)
    assert any("configured_customer" in row and "FAIL" in row for row in rows)
