"""Expose model-formatted Spider values without native normalization/validation."""

from copy import deepcopy


def extraction_report(doc, cfg, response):
    profile = cfg.get("profiles", {}).get(doc.doc_type)
    if not profile:
        return {
            "document_type": doc.doc_type,
            "status": "NEEDS_CLASSIFICATION",
            "normalized": {},
            "fields": {},
            "issues": [{"code": "UNKNOWN_PROFILE", "message": f"Document profile '{doc.doc_type}' is not configured."}],
        }
    raw = deepcopy(response.get("extract_result") or {})
    effective = deepcopy(raw)
    effective.pop("page_results", None)
    # Reviewer changes are explicit audited inputs, not automatic normalization.
    effective.update(deepcopy(doc.overrides or {}))
    keys = dict.fromkeys(
        [key for key, _ in profile.get("columns", [])] + list(effective)
    )
    report = {
        "document_type": doc.doc_type,
        "status": "SKIPPED",
        "processing_mode": "spider_extraction_formatted",
        "normalization": {"status": "SKIPPED", "handled_by": "model_extraction"},
        "validation": {"status": "SKIPPED", "reason": "Spider-AI provider bypass"},
        # Historical API name; this is an unchanged model value projection.
        "normalized": effective,
        "original_raw": raw,
        "review_overrides": deepcopy(doc.overrides),
        "corrections": [],
        "fields": {
            key: {
                "raw_value": deepcopy(raw.get(key)),
                "normalized_value": deepcopy(effective.get(key)),
                "status": "SKIPPED",
                "issues": [],
            }
            for key in keys
        },
    }
    from .configuration.field_checks import apply_field_checks
    from .enum_aliases import apply_requested_aliases
    report = apply_requested_aliases(report, doc, profile)
    return apply_field_checks(report, profile)
