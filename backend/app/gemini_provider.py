"""Google Gemini multimodal extraction provider with canonical contract normalization."""

import base64
import json
import logging
import re
import time
import httpx
import fitz

from .db import SessionLocal
from .crypto import decrypt
from .storage import store, original_key, fitz_open_original
from .extraction_prompts import (
    DEFAULT_INSTRUCTION,
    reading_instructions,
)
from .extraction.connector_repository import SqlConnectorRepository
from .provider import ProcessingIssue
from .spider_provider import (
    field_catalog,
    field_guidance,
    field_types,
    _render_page_jpeg,
)

log = logging.getLogger("sqe.gemini")


def _sanitize_box_2d(coords):
    """Ensure box_2d is 4 coordinates in 0..1000 range, y0 < y1, x0 < x1."""
    if not isinstance(coords, (list, tuple)) or len(coords) != 4:
        return None
    try:
        y0, x0, y1, x1 = [float(v) for v in coords]
    except (ValueError, TypeError):
        return None

    # If coordinates are 0.0..1.0 normalized, scale to 0..1000
    if max(y0, x0, y1, x1) <= 1.0 and (y1 > y0 or x1 > x0):
        y0, x0, y1, x1 = y0 * 1000.0, x0 * 1000.0, y1 * 1000.0, x1 * 1000.0

    # Clamp to 0..1000
    y0 = max(0.0, min(1000.0, y0))
    x0 = max(0.0, min(1000.0, x0))
    y1 = max(0.0, min(1000.0, y1))
    x1 = max(0.0, min(1000.0, x1))

    # Ensure min order
    if y0 >= y1:
        y1 = min(1000.0, y0 + 10.0)
    if x0 >= x1:
        x1 = min(1000.0, x0 + 10.0)

    return [int(round(y0)), int(round(x0)), int(round(y1)), int(round(x1))]


def _canonicalize_locations(raw_locations, default_page=1):
    """Normalize any Gemini location format into the canonical array:
    [{'field': field, 'page_number': page, 'box_2d': [y0, x0, y1, x1]}].
    """
    canonical = []
    if isinstance(raw_locations, list):
        for item in raw_locations:
            if not isinstance(item, dict):
                continue
            field_name = item.get("field")
            if not field_name:
                continue
            box = item.get("box_2d") or item.get("bbox") or item.get("box")
            clean_box = _sanitize_box_2d(box)
            if clean_box:
                page = item.get("page_number", default_page)
                try:
                    page = int(page) if int(page) >= 1 else default_page
                except (ValueError, TypeError):
                    page = default_page
                canonical.append({
                    "field": str(field_name),
                    "page_number": page,
                    "box_2d": clean_box,
                })
    elif isinstance(raw_locations, dict):
        for field_name, value in raw_locations.items():
            if isinstance(value, dict):
                box = value.get("box_2d") or value.get("bbox") or value.get("box")
                page = value.get("page_number", default_page)
                try:
                    page = int(page) if int(page) >= 1 else default_page
                except (ValueError, TypeError):
                    page = default_page
            elif isinstance(value, (list, tuple)):
                box = value
                page = default_page
            else:
                continue

            clean_box = _sanitize_box_2d(box)
            if clean_box:
                canonical.append({
                    "field": str(field_name),
                    "page_number": page,
                    "box_2d": clean_box,
                })

    return canonical


def normalize_gemini_json(raw_text, default_doc_type=None):
    """Sanitize and parse JSON from Gemini, handling markdown code fences."""
    text = (raw_text or "").strip()
    # Strip markdown ```json ... ``` or ``` ... ```
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        # Fallback regex extraction of JSON object
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
            except json.JSONDecodeError:
                raise ProcessingIssue(f"Gemini returned non-JSON text: {text[:200]}") from exc
        else:
            raise ProcessingIssue(f"Gemini returned non-JSON text: {text[:200]}") from exc

    if not isinstance(data, dict):
        raise ProcessingIssue("Gemini response did not contain a JSON object.")

    # Canonicalize output structure
    if "extract_result" in data and isinstance(data["extract_result"], dict):
        extract_result = data["extract_result"]
        classification = data.get("classification")
        locations = data.get("_field_locations") or data.get("field_locations") or extract_result.get("_field_locations") or {}
    else:
        # Whole object is extract result
        extract_result = {k: v for k, v in data.items() if k not in {"classification", "_field_locations", "field_locations"}}
        classification = data.get("classification")
        locations = data.get("_field_locations") or data.get("field_locations") or {}

    # Canonicalize classification
    if isinstance(classification, str):
        classification = {"doc_type": classification, "confidence": 1.0}
    elif isinstance(classification, dict):
        if "doc_type" not in classification and "type" in classification:
            classification["doc_type"] = classification["type"]
        if "confidence" not in classification:
            classification["confidence"] = 1.0
    elif default_doc_type:
        classification = {"doc_type": default_doc_type, "confidence": 1.0}
    else:
        classification = None

    # Canonicalize locations
    canonical_locations = _canonicalize_locations(locations)

    # Attach canonical locations inside extract_result for spatial_grounding.split_locations
    extract_result["_field_locations"] = canonical_locations

    return extract_result, classification, canonical_locations


def _extract_google_error(resp):
    """Extract human-readable error message from Google API error response."""
    try:
        err_json = resp.json()
        if isinstance(err_json, dict) and "error" in err_json:
            err = err_json["error"]
            if isinstance(err, dict) and "message" in err:
                return err["message"]
            return str(err)
    except Exception:
        pass
    return resp.text[:300]


def run_gemini(doc, cfg, heartbeat):
    """Execute document classification and extraction with Google Gemini."""
    connection = SqlConnectorRepository(SessionLocal, decrypt).read(doc.org, "gemini")
    key, options = connection.api_key, connection.options
    if not key:
        raise ProcessingIssue(
            "Google Gemini API key is not configured. Register it under Settings -> AI Connectors & Credentials."
        )

    base_url = options.get("base_url", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
    raw_model = options.get("model_id", "gemini-2.5-pro")
    model_id = raw_model.strip().removeprefix("models/")
    timeout = options.get("timeout_seconds", 120)
    max_pixels = options.get("image_max_pixels", 2400)
    jpeg_quality = options.get("image_jpeg_quality", 85)

    # 1. Render pages to JPEG
    page_images = []
    with fitz_open_original(store().read(original_key(doc))) as pdf:
        page_count = len(pdf)
        if page_count < 1 or page_count > 30:
            raise ProcessingIssue("Gemini extraction supports 1-30 pages per document.")
        for number, page in enumerate(pdf, 1):
            heartbeat()
            data = _render_page_jpeg(page, number, max_pixels, jpeg_quality, max_image_bytes=4 * 1024 * 1024)
            page_images.append(data)

    heartbeat()

    # 2. Automated Multimodal Classification if doc_type is unknown or unconfigured
    classification = getattr(doc, "classification", None) or {}
    profiles_cfg = cfg.get("profiles", {})
    if doc.doc_type not in profiles_cfg or doc.doc_type == "unknown":
        log.info("Document %s has unmapped doc_type '%s'; running Gemini classification", doc.id, doc.doc_type)
        labels = {
            name: p.get("classification_description") or p.get("label") or name
            for (name, p) in profiles_cfg.items()
        }
        classify_prompt = (
            "You are an expert banking document classifier.\n"
            "Analyze the visual header, title, layout, and text of the provided document image.\n"
            "Classify this document into EXACTLY ONE of the following supported document types:\n"
            f"{json.dumps(labels, indent=2)}\n\n"
            "Return ONLY a JSON object with this exact structure:\n"
            '{"type": "document_type_key", "confidence": 0.95, "reason": "brief explanation"}\n'
            "If the document definitely does not match any of the supported types, return type 'unknown'."
        )

        page1_b64 = base64.b64encode(page_images[0]).decode("ascii")
        classify_url = f"{base_url}/models/{model_id}:generateContent?key={key}"
        classify_payload = {
            "contents": [
                {
                    "parts": [
                        {"text": classify_prompt},
                        {"inlineData": {"mimeType": "image/jpeg", "data": page1_b64}},
                    ]
                }
            ],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
        }

        try:
            with httpx.Client(timeout=45.0) as client:
                c_resp = client.post(classify_url, json=classify_payload)
            if c_resp.status_code == 200:
                c_data = c_resp.json()
                c_parts = c_data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                c_text = "".join([p.get("text", "") for p in c_parts])
                try:
                    c_clean = re.sub(r"^```(?:json)?\s*", "", c_text.strip(), flags=re.IGNORECASE)
                    c_clean = re.sub(r"\s*```$", "", c_clean).strip()
                    c_json = json.loads(c_clean)
                    actual_type = c_json.get("type")
                    conf = float(c_json.get("confidence", 0.0))
                except Exception:
                    actual_type = None
                    conf = 0.0

                if actual_type and actual_type in profiles_cfg and conf >= 0.70:
                    log.info("Gemini classified document %s as '%s' (confidence: %.2f)", doc.id, actual_type, conf)
                    doc.doc_type = actual_type
                    classification = {
                        "method": "gemini",
                        "doc_type": actual_type,
                        "confidence": conf,
                        "confirmed": True,
                        "reason": c_json.get("reason"),
                    }
                    with SessionLocal.begin() as db:
                        from .db import Document as DbDoc
                        db_d = db.get(DbDoc, doc.id)
                        if db_d:
                            db_d.doc_type = actual_type
                            db_d.classification = classification
                else:
                    log.warning("Gemini classification failed or confidence low for %s: %s (%.2f)", doc.id, actual_type, conf)
                    with SessionLocal.begin() as db:
                        from .db import Document as DbDoc
                        db_d = db.get(DbDoc, doc.id)
                        if db_d:
                            db_d.status = "NEEDS_CLASSIFICATION"
                            db_d.error = "Document classification needs confirmation before extraction."
                            db_d.classification = {
                                "method": "gemini",
                                "doc_type": "unknown",
                                "confidence": conf,
                                "candidate": actual_type,
                            }
                    return None, {"method": "gemini", "doc_type": "unknown", "confidence": conf}
            else:
                log.warning("Gemini classification returned status %d", c_resp.status_code)
        except Exception as exc:
            log.error("Classification error with Gemini for doc %s: %s", doc.id, exc)
            with SessionLocal.begin() as db:
                from .db import Document as DbDoc
                db_d = db.get(DbDoc, doc.id)
                if db_d:
                    db_d.status = "NEEDS_CLASSIFICATION"
                    db_d.error = f"Classification interrupted: {exc}"
            return None, {"method": "gemini", "doc_type": "unknown", "confidence": 0.0}

    heartbeat()

    # 3. Build extraction prompt
    profile = cfg.get("profiles", {}).get(doc.doc_type, {})
    schema = profile.get("schema", {})
    system_text = (
        profile.get("system_prompt")
        or profile.get("system_instruction")
        or DEFAULT_INSTRUCTION
    )
    instruction_payload = {
        "target_document_type": doc.doc_type,
        "schema_catalog": field_catalog(schema),
        "field_instructions": field_guidance(schema),
        "field_types": field_types(schema),
        "reading_guidance": reading_instructions(profile),
    }

    user_text = (
        f"{system_text}\n\n"
        "Analyze the provided document page images carefully. Extract all requested fields exactly according to the schema.\n"
        "Return ONLY a valid JSON object with the following top-level structure:\n"
        "{\n"
        '  "extract_result": { <extracted fields conforming to schema> },\n'
        '  "classification": { "doc_type": "' + doc.doc_type + '", "confidence": 1.0 },\n'
        '  "_field_locations": [\n'
        '    { "field": "<field_path>", "page_number": 1, "box_2d": [ymin, xmin, ymax, xmax] }\n'
        '  ]\n'
        "}\n\n"
        "Note on coordinates: box_2d should be [ymin, xmin, ymax, xmax] scaled 0 to 1000 relative to page dimensions.\n\n"
        "SCHEMA & FIELD INSTRUCTIONS:\n" + json.dumps(instruction_payload, indent=2)
    )

    # 3. Call Gemini
    # Check if OpenAI-compatible proxy or native Google REST endpoint
    is_openai_mode = "openai" in base_url or base_url.endswith("/v1")

    headers = {"Content-Type": "application/json"}
    if is_openai_mode:
        headers["Authorization"] = f"Bearer {key}"
        url = f"{base_url}/chat/completions"
        content_parts = [{"type": "text", "text": user_text}]
        for img_bytes in page_images:
            b64 = base64.b64encode(img_bytes).decode("ascii")
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
            })
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": content_parts}],
            "temperature": options.get("temperature", 0.1),
            "max_tokens": options.get("max_tokens", 16384),
        }
    else:
        # Native Google Generative Language REST API
        url = f"{base_url}/models/{model_id}:generateContent?key={key}"
        parts = [{"text": user_text}]
        for img_bytes in page_images:
            b64 = base64.b64encode(img_bytes).decode("ascii")
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": b64
                }
            })
        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": options.get("temperature", 0.1),
                "topP": options.get("top_p", 0.95),
                "maxOutputTokens": options.get("max_tokens", 16384),
                "responseMimeType": "application/json",
            }
        }

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 503 and is_openai_mode and model_id == "pct-prod-spider/pecut/gemini-3.8-flash-high":
                log.warning(
                    "Google Gemini / OpenAI endpoint returned HTTP 503 for model '%s'. Falling back to 'pct-prod-spider/pecut/gemini-4-argon'.",
                    model_id,
                )
                fallback_payload = dict(payload)
                fallback_payload["model"] = "pct-prod-spider/pecut/gemini-4-argon"
                resp = client.post(url, headers=headers, json=fallback_payload)
            if resp.status_code != 200:
                err_msg = _extract_google_error(resp)
                raise ProcessingIssue(f"Google Gemini request failed ({resp.status_code}): {err_msg}")
            resp_data = resp.json()
    except httpx.RequestError as exc:
        raise ProcessingIssue(f"Network error connecting to Google Gemini: {exc}") from exc

    # 4. Extract generated text
    if is_openai_mode:
        choices = resp_data.get("choices", [])
        if not choices:
            raise ProcessingIssue("Gemini returned no completions.")
        raw_output = choices[0].get("message", {}).get("content", "")
    else:
        candidates = resp_data.get("candidates", [])
        if not candidates:
            block_reason = resp_data.get("promptFeedback", {}).get("blockReason")
            if block_reason:
                raise ProcessingIssue(f"Google Gemini blocked the document prompt: {block_reason}")
            raise ProcessingIssue("Gemini returned no candidate outputs.")

        first_cand = candidates[0]
        finish_reason = first_cand.get("finishReason")
        if finish_reason in {"SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT"}:
            raise ProcessingIssue(f"Google Gemini output blocked: finish_reason={finish_reason}")

        content = first_cand.get("content", {})
        parts = content.get("parts", [])
        raw_output = "".join(part.get("text", "") for part in parts if isinstance(part, dict) and "text" in part)

    # 5. Normalize
    extract_result, classification, locations = normalize_gemini_json(raw_output, default_doc_type=doc.doc_type)

    if not classification:
        classification = {"doc_type": doc.doc_type, "confidence": 1.0}

    response_payload = {
        "extract_result": extract_result,
        "_field_locations": locations,
        "page_count": page_count,
        "provider": "gemini",
        "model": model_id,
    }

    return response_payload, classification


def test_gemini_ping(api_key, base_url, model_id):
    """Verify Gemini connection and credentials with a 1-token probe request."""
    start = time.time()
    clean_model = model_id.strip().removeprefix("models/")
    clean_key = (api_key or "").strip()
    clean_url = (base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
    url = f"{clean_url}/models/{clean_model}:generateContent?key={clean_key}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": "ping"}]}],
        "generationConfig": {"maxOutputTokens": 2}
    }
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(url, json=payload)
            latency_ms = int((time.time() - start) * 1000)
            if resp.status_code == 200:
                return {"success": True, "latency_ms": latency_ms, "model": clean_model}
            err_msg = _extract_google_error(resp)
            return {"success": False, "error": f"HTTP {resp.status_code}: {err_msg[:200]}"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
