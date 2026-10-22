"""Checkpoint external side effects before submission; never blindly recreate jobs."""

import copy
import io
import json
import time

from llama_cloud import APIError, LlamaCloud
from sqlalchemy import select

from .configuration.profiles import profile_schema, schema_report
from .db import Connector, Document, SessionLocal
from .domain import LABELS, get_profile, serial
from .security import decrypt
from .settings import ROOT, settings
from .storage import original_key, object_key, store


from .extraction.contracts import ProcessingIssue


def checkpoint(doc_id, status=None, **state):
    from .extraction.state_repository import SqlProviderState
    SqlProviderState(SessionLocal).checkpoint(doc_id, status, **state)


def state_of(doc_id):
    from .extraction.state_repository import SqlProviderState
    return SqlProviderState(SessionLocal).read(doc_id)


def fixture_response(doc_type):
    """Explicit synthetic fixtures, never claimed to be OCR of the uploaded PDF."""
    if doc_type not in LABELS:
        raise ProcessingIssue("Fixture mode requires a supported document type.")
    return json.loads(
        (ROOT / "backend/fixtures" / (doc_type + ".json")).read_text(encoding="utf-8")
    )


def run_provider(doc, cfg, heartbeat):
    """Compatibility facade; callers transition through the application service."""
    from .extraction.service import extract_document
    result = extract_document(doc, cfg, heartbeat)
    return result.response, result.classification


def run_fixture(doc, cfg, heartbeat):
    if settings.environment != "development":
        raise ProcessingIssue("Fixture processing is disabled outside development.")
    if doc.doc_type == "unknown":
        raise ProcessingIssue(
            "Fixture mode requires a recognized filename or manually assigned document type."
        )
    checkpoint(doc.id, "EXTRACTING", fixture=True)
    heartbeat()
    return fixture_response(doc.doc_type), {
        "method": "fixture",
        "type": doc.doc_type,
        "reason": "Synthetic development fixture. No document content was classified or extracted.",
        "confirmed": False,
    }


def run_llama(doc, cfg, heartbeat):
    from .extraction.connector_repository import SqlConnectorRepository
    connection = SqlConnectorRepository(SessionLocal, decrypt).read(doc.org, "llama")
    key, options = connection.api_key, connection.options
    if not key:
        raise ProcessingIssue(
            "LlamaCloud API key is not configured. Open Settings → Connector, save the key, then retry."
        )
    scope = {
        k: v for k, v in options.items() if k in {"project_id", "organization_id"} and v
    }
    kwargs = {"api_key": key, "max_retries": 0, "timeout": options["timeout_seconds"]}
    if options.get("base_url"):
        kwargs["base_url"] = options["base_url"]
    steps = {s["action"]: s for s in cfg.get("workflow", [])}
    with LlamaCloud(**kwargs) as client:

        def read_with_retry(operation, retries=2):
            for attempt in range(retries + 1):
                heartbeat()
                try:
                    return operation()
                except APIError as exc:
                    code = getattr(exc, "status_code", None)
                    if code is not None and code != 429 and code < 500:
                        raise
                    if attempt == retries:
                        raise
                    time.sleep(2**attempt)

        def create_once(name, operation, stage, manifest=None):
            state = state_of(doc.id)
            if state.get(name):
                saved=state.get(name+'_prompt_manifest')
                if manifest and saved and manifest!=saved:
                    raise ProcessingIssue('Saved provider job used different profile prompts. Start a new field reprocessing request; no new paid job was created.')
                return state[name]
            if state.get("pending_create"):
                raise ProcessingIssue(
                    "An earlier provider submission has an uncertain outcome. Reconcile its job ID before retrying; no new paid job was created."
                )
            checkpoint(doc.id, stage, pending_create=name, provider_stage=stage)
            heartbeat()
            try:
                result = operation()
            except APIError as exc:
                if getattr(exc, "status_code", 0) in {400, 401, 403, 404, 422, 429}:
                    checkpoint(doc.id, pending_create=None)
                raise
            checkpoint(doc.id, pending_create=None, **{name: result.id,**({name+'_prompt_manifest':manifest} if manifest else {})})
            return result.id

        def wait(stage, job_id):
            checkpoint(doc.id, provider_stage=stage.upper() + "_POLL")
            step = steps.get(stage, {})
            retries = step.get("read_poll_retries", 2)
            started = time.monotonic()
            while True:
                heartbeat()
                if stage == "classify":
                    result = read_with_retry(
                        lambda: client.classify.get(job_id, **scope), retries
                    )
                    job = result
                elif stage == "parse":
                    result = read_with_retry(
                        lambda: client.parsing.get(job_id, **scope), retries
                    )
                    job = result.job
                else:
                    result = read_with_retry(
                        lambda: client.extract.get(job_id, **scope), retries
                    )
                    job = result
                if job.status == "COMPLETED":
                    return result
                if job.status in {"FAILED", "CANCELLED"}:
                    raise ProcessingIssue(
                        f"LlamaCloud {stage} job {job.status}. Saved job ID: {job_id}."
                    )
                if time.monotonic() - started > step.get("timeout_seconds", 1200):
                    raise ProcessingIssue(
                        f"LlamaCloud {stage} is still running. Retry resumes saved job {job_id}."
                    )
                time.sleep(3)

        # Read storage before marking a paid provider submission as pending.
        file_data = (
            store().read(original_key(doc))
            if not state_of(doc.id).get("file_id")
            else b""
        )
        file_id = create_once(
            "file_id",
            lambda: client.files.create(
                file=(
                    "original.pdf",
                    io.BytesIO(file_data),
                    "application/pdf",
                ),
                purpose="parse",
                **scope,
            ),
            "UPLOADING",
        )
        classification = doc.classification
        if not classification.get("manual"):
            classify_id = create_once(
                "classify_job_id",
                lambda: client.classify.create(
                    file_input=file_id,
                    transaction_id=f"sqe-classify-{doc.id}",
                    configuration={
                        "rules": [
                            {
                                "type": name,
                                "description": cfg["profiles"][name].get(
                                    "classification_description", cfg["profiles"][name].get("label", name)
                                ),
                            }
                            for name in cfg["profiles"]
                        ]
                    },
                    **scope,
                ),
                "CLASSIFYING",
            )
            classified = wait("classify", classify_id)
            result = classified.result
            content = result.model_dump(mode="json") if result else {}
            classification = {
                "method": "llama",
                **content,
                "job_id": classify_id,
                "confirmed": True,
            }
            actual_type = content.get("type")
            confidence = content.get("confidence")
            strong = (
                isinstance(confidence, (int, float))
                and steps.get("classify", {})
                .get("parameters", {})
                .get("minimum_confidence", cfg.get("classification_threshold", 0.85))
                <= confidence
                <= 1
            )
            mismatch = doc.doc_type != "unknown" and actual_type != doc.doc_type
            with SessionLocal.begin() as db:
                stored = db.get(Document, doc.id)
                stored.classification = classification
                if actual_type not in cfg["profiles"] or not strong or mismatch:
                    stored.status = "NEEDS_CLASSIFICATION"
                    stored.error = "Classification needs review: low confidence, unknown type or filename/content disagreement."
                    return None, classification
                stored.doc_type = actual_type
                doc.doc_type = actual_type
        profile = cfg["profiles"][doc.doc_type]
        from .location_learning import retrieve, prompt as location_prompt

        state = state_of(doc.id)
        if "location_guidance" not in state:
            with SessionLocal() as db:
                hints = (
                    retrieve(
                        db,
                        doc,
                        {
                            **profile,
                            "schema": profile.get("schema")
                            or profile_schema(cfg, doc.doc_type),
                        },
                    )
                    if not state.get("parse_job_id")
                    else []
                )
            checkpoint(doc.id, location_guidance=hints, location_guidance_version=1)
        else:
            hints = state["location_guidance"]
        guidance = location_prompt(hints)
        from run import extract_config, parse_config

        parse_options = parse_config(
            steps.get("parse", {}).get("parameters", {}).get("tier", cfg["parse_tier"]),
            steps.get("parse", {})
            .get("parameters", {})
            .get("version", cfg["parse_version"]),
            doc.doc_type,
        )
        from .extraction_prompts import llama_parse_instructions, llama_extract_instructions, prompt_manifest
        parse_options["agentic_options"]["custom_prompt"] = llama_parse_instructions(profile,guidance)
        extract_options = extract_config(
            steps.get("extract", {})
            .get("parameters", {})
            .get("tier", cfg["extract_tier"]),
            cfg["extract_version"],
            doc.doc_type,
        )
        extract_options["system_prompt"] = llama_extract_instructions(profile,guidance=guidance)
        extract_options["data_schema"] = profile.get(
            "schema", extract_options["data_schema"]
        )
        from .spatial_grounding import spatial_schema
        extract_options["data_schema"] = spatial_schema(extract_options["data_schema"])
        # Classify may use generic parsing; extraction needs the pinned document-specific form prompt.
        # Therefore this release explicitly creates a specialized parse instead of assuming compatibility.
        parse_id = create_once(
            "parse_job_id",
            lambda: client.parsing.create(file_id=file_id, **parse_options, **scope),
            "PARSING",
            manifest=prompt_manifest(profile,extract_options['data_schema'],guidance=guidance),
        )
        checkpoint(doc.id, "PARSING")
        wait("parse", parse_id)
        state = state_of(doc.id)
        parse_key = state.get("parse_response_key")
        if not parse_key or state.get("parse_response_job_id") != parse_id:
            checkpoint(doc.id, provider_stage="PARSE_RESULT")
            parsed = read_with_retry(
                lambda: client.parsing.get(
                    parse_id,
                    expand=["forms", "items", "text", "markdown", "metadata"],
                    **scope,
                )
            )
            parsed_result = parsed.model_dump(mode="json")
            if parsed_result.get("job", {}).get("status") != "COMPLETED":
                raise ProcessingIssue(
                    "Parse result is not completed; retry using its saved job ID."
                )
            import hashlib

            parse_key = object_key(
                doc.org,
                doc.branch_id,
                "documents",
                doc.id,
                "parse-" + hashlib.sha256(parse_id.encode()).hexdigest()[:24] + ".json",
            )
            store().put(
                parse_key,
                json.dumps(parsed_result, ensure_ascii=False).encode("utf-8"),
                "application/json",
            )
            checkpoint(
                doc.id, parse_response_key=parse_key, parse_response_job_id=parse_id
            )
        extract_id = create_once(
            "extract_job_id",
            lambda: client.extract.create(
                file_input=parse_id, configuration=extract_options, **scope
            ),
            "EXTRACTING",
            manifest=prompt_manifest(profile,extract_options['data_schema'],guidance=guidance),
        )
        checkpoint(doc.id, "EXTRACTING")
        wait("extract", extract_id)
        checkpoint(doc.id, provider_stage="EXTRACT_RESULT")
        response = read_with_retry(
            lambda: client.extract.get(
                extract_id,
                expand=["extract_metadata", "configuration", "usage"],
                **scope,
            )
        )
        checkpoint(doc.id, provider_error=None)
        result = response.model_dump(mode="json")
        final_state=state_of(doc.id)
        result["extract_metadata"] = {
            **(result.get("extract_metadata") or {}),
            "location_guidance": hints,
            "location_guidance_version": 1,
            "prompt_usage": {stage:{'manifest':final_state.get(stage+'_prompt_manifest'),
                'status':'RECORDED' if final_state.get(stage+'_prompt_manifest') else 'LEGACY_OR_UNRECORDED'}
                for stage in ['parse_job_id','extract_job_id']},
        }
        result["parse_response_key"] = parse_key
        return result, classification


def validate_extraction(doc, cfg, response, authoritative=None):
    if cfg["profiles"][doc.doc_type].get("validation_adapter") == "schema":
        return schema_report(doc, cfg, response)
    if cfg.get("provider") == "spider-ai":
        from .spider_result import extraction_report

        return extraction_report(doc, cfg, response)
    from datetime import datetime
    from zoneinfo import ZoneInfo

    profile = get_profile(doc.doc_type)
    raw = response["extract_result"]
    effective = copy.deepcopy(raw)
    effective.pop("_visual_evidence", None)
    effective.update(doc.overrides)
    kwargs = {"validation_context": {}} if doc.doc_type != "application" else {}
    if doc.doc_type == "application" and authoritative:
        kwargs["validation_context"] = {"authoritative": authoritative}
    if doc.doc_type in {"ektp", "valas_declaration_1", "valas_declaration_2", "riplay"}:
        kwargs["extract_job_id"] = response.get("id")
    if doc.doc_type == "riplay":
        kwargs["validation_context"] = {"defer_identity_to_case": True}
    policy = copy.deepcopy(cfg["profiles"][doc.doc_type]["policy"])
    if doc.doc_type == "ektp" and "normalization_enum_aliases" in getattr(
        doc, "provider_state", {}
    ):
        policy["enum_aliases"] = copy.deepcopy(
            doc.provider_state["normalization_enum_aliases"]
        )
        policy["enum_raw_fallback_fields"] = copy.deepcopy(
            doc.provider_state.get(
                "normalization_enum_raw_fallback_fields", ["religion"]
            )
        )
    native_fields=set(profile['schema']['properties'])
    report = profile["validate"](
        {k:v for k,v in effective.items() if k in native_fields},
        response.get("extract_metadata"),
        policy,
        datetime.now(ZoneInfo("Asia/Jakarta")).date(),
        cfg["name_directory"],
        **kwargs,
    )
    report["document_type"] = doc.doc_type
    report["original_raw"] = raw
    report["review_overrides"] = doc.overrides
    # Registered native validators do not know optional profile extension fields.
    core = set(profile['schema']['properties'])
    for key in set(cfg['profiles'][doc.doc_type].get('schema', profile['schema'])['properties']) - core:
        value = effective.get(key)
        if key in effective:
            from .schema_descriptions import validate_extension_value
            validate_extension_value(value,cfg['profiles'][doc.doc_type]['schema']['properties'][key],key)
        report['normalized'][key] = value
        report.setdefault('fields', {})[key] = {'raw_value':raw.get(key),'normalized_value':value,
            'status':'REVIEW' if value is None else 'PASS','issues':[]}
    return serial(report)
