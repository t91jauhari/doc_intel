"""Configuration HTTP boundary; application services own publication and replay."""

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.db import Case, SessionLocal
from app.configuration.revisions import latest_config
from app.configuration.validation import validate_config
from app.security import authorized, current_user, require_roles
from app.settings import settings
from app.configuration.profiles import profile_schema
from app.configuration.repository import get_revision

router = APIRouter(tags=["configuration"])
ADMIN = require_roles("bank_admin")


@router.get("/api/config")
def configuration(user=Depends(current_user)):
    from app.schema_descriptions import with_schemas
    import copy

    with SessionLocal() as db:
        cfg = latest_config(db, user.org, copy_payload=False)
        payload = with_schemas(
            cfg.payload,
            {
                name: {"schema": profile_schema(cfg.payload, name)}
                for name in cfg.payload["profiles"]
            },
        )
        if isinstance(payload.get("profiles"), dict):
            payload["profiles"].pop("invoice_1", None)
            payload["profiles"].pop("invoice_2", None)
        if "invoice" in payload.get("profiles", {}):
            inv = payload["profiles"]["invoice"]
            payload.setdefault("invoice_profiles", {})
            if "invoice_1" not in payload["invoice_profiles"]:
                payload["invoice_profiles"]["invoice_1"] = {
                    "label": "Underlying Invoice 1",
                    "columns": [
                        ["from_name", "Company Name (Header)"],
                        ["from_address", "Company Address"],
                        ["to_name", "Bill To Name"],
                        ["to_address", "Bill To Address"],
                        ["to_phone", "Bill To Phone"],
                        ["ship_to_name", "Ship To Name"],
                        ["ship_to_address", "Ship To Address"],
                        ["ship_to_phone", "Ship To Phone"],
                        ["invoice_number", "Invoice Number\n(what if the underlying is not an invoice)"],
                        ["invoice_date", "Invoice Date\n(what if the underlying is not an invoice)"],
                        ["due_date", "Due Date"],
                        ["item_name", "Item Description"],
                        ["quantity", "Quantity"],
                        ["unit_price", "Unit Price"],
                        ["final_total_amount", "Total"],
                        ["subtotal_all_items", "Subtotal"],
                        ["discount", "Discount"],
                        ["subtotal_less_discount", "Subtotal Less Discount"],
                        ["shipping_handling", "Shipping/Handling"],
                        ["beneficiary_name", "Beneficiary Name"],
                        ["bank_account_number", "Account Number"],
                        ["bank_name", "Beneficiary Bank"],
                        ["bank_address", "Address Bank"],
                        ["swift_code", "Beneficary Bank SWIFT Code"],
                    ],
                    "schema": copy.deepcopy(inv.get("schema", {})),
                    "policy": copy.deepcopy(inv.get("policy", {})),
                    "system_prompt": inv.get("system_prompt", ""),
                    "parse_prompt": inv.get("parse_prompt", ""),
                }
            if "invoice_2" not in payload["invoice_profiles"]:
                payload["invoice_profiles"]["invoice_2"] = {
                    "label": "Underlying Invoice 2",
                    "columns": [
                        ["to_name", "To (Customer Name)"],
                        ["to_address", "To Address"],
                        ["to_phone", "To Phone"],
                        ["from_name", "From (Company Name)"],
                        ["from_address", "From Address"],
                        ["from_phone", "From Phone"],
                        ["bank_name", "Bank Name (Payment Note)"],
                        ["swift_code", "SWIFT Code"],
                        ["bank_account_number", "Bank Account Number"],
                        ["invoice_date", "Invoice Date"],
                        ["due_date", "Due Date"],
                        ["invoice_number", "Invoice Number"],
                        ["item_name", "Item Name"],
                        ["quantity", "Quantity"],
                        ["unit_price", "Unit Price"],
                        ["subtotal", "Subtotal"],
                        ["subtotal_all_items", "Subtotal (All Items)"],
                        ["final_total_amount", "Final Total Amount"],
                        ["claim_note", "Claim No.2 (60% of Supply Equipment) Claim Note / Material Arrived at Site"],
                    ],
                    "schema": copy.deepcopy(inv.get("schema", {})),
                    "policy": copy.deepcopy(inv.get("policy", {})),
                    "system_prompt": inv.get("system_prompt", ""),
                    "parse_prompt": inv.get("parse_prompt", ""),
                }
            payload.setdefault("invoice_signatures", {
                "invoice_2_terms": [
                    "claim no",
                    "supply equipment",
                    "material arrived at site",
                    "pt tiga utama",
                    "chem co",
                    "dokumen underlying",
                ],
                "invoice_1_terms": [
                    "ship to",
                    "bill to",
                    "subtotal less discount",
                    "shipping/handling",
                ],
            })
        return JSONResponse({
            "id": cfg.id,
            "version": cfg.version,
            "payload": payload,
            "can_edit": user.role == "bank_admin",
        })


class ConfigInput(BaseModel):
    expected_version: int
    payload: dict


@router.post("/api/config/publish")
def publish_config(data: ConfigInput, user=Depends(ADMIN)):
    if isinstance(data.payload.get("profiles"), dict):
        data.payload["profiles"].pop("invoice_1", None)
        data.payload["profiles"].pop("invoice_2", None)
    from app.configuration.publication import (
        publish_configuration,
        ConfigurationStorageNotReady,
    )
    from app.configuration.service import StaleConfiguration

    try:
        with SessionLocal.begin() as db:
            return publish_configuration(
                db,
                organization=user.org,
                actor=user.id,
                expected_version=data.expected_version,
                payload=data.payload,
                storage_mode=settings.configuration_storage_mode,
            )
    except StaleConfiguration as exc:
        raise HTTPException(409, str(exc)) from exc
    except ConfigurationStorageNotReady as exc:
        raise HTTPException(503, str(exc)) from exc
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(422, str(exc))


@router.post("/api/config/test")
def test_config(data: ConfigInput, user=Depends(ADMIN)):
    if isinstance(data.payload.get("profiles"), dict):
        data.payload["profiles"].pop("invoice_1", None)
        data.payload["profiles"].pop("invoice_2", None)
    from app.configuration.replay import replay_configuration

    try:
        validate_config(data.payload)
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(422, str(exc))
    with SessionLocal() as db:
        return replay_configuration(db, organization=user.org, payload=data.payload)


@router.get("/api/config/catalog")
def configuration_catalog(case_id: str | None = None, user=Depends(current_user)):
    from app.sop import CATEGORIES, OPERATORS, fields, approved_scope
    from app.configuration.contexts import definitions, enum_options
    from app.configuration.dataset_policy import comparison_policy
    from app.configuration.scoring import defaults as scoring_defaults

    with SessionLocal() as db:
        case = authorized(db, Case, case_id, user) if case_id else None
        config = (
            get_revision(db, case.config_id, copy_payload=False) if case else latest_config(db, user.org, copy_payload=False)
        )
        family = (
            config.payload["templates"][case.template].get("document_family", "forex")
            if case
            else None
        )
        context_definitions = definitions(config.payload, family)
    return {
        "score_groups": scoring_defaults(),
        "fields": fields(),
        "scope": approved_scope(),
        "operators": {k: sorted(v) if v else None for k, v in OPERATORS.items()},
        "context": enum_options(config.payload, family),
        "context_definitions": {
            key: value.model_dump(mode="json")
            for key, value in context_definitions.items()
        },
        "config_version": config.version,
        "dataset_comparison_policy": comparison_policy().model_dump(mode="json"),
        "categories": (*CATEGORIES, "DOCUMENT_VERIFICATION", "OBSERVATIONS"),
    }


@router.get("/api/config/export")
def configuration_export(user=Depends(ADMIN)):
    from app.config_workbook import MIME, export_config
    from app.sop import defaults

    with SessionLocal() as db:
        cfg = latest_config(db, user.org)
        try:
            data = export_config({**defaults(), **cfg.payload})
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
    return Response(
        data,
        media_type=MIME,
        headers={
            "Content-Disposition": 'attachment; filename="document-workflow-config.xlsx"'
        },
    )


@router.post("/api/config/import")
async def configuration_import(file: UploadFile = File(), user=Depends(ADMIN)):
    from app.config_workbook import import_config
    from app.sop import defaults

    data = await file.read(2_000_001)
    if len(data) > 2_000_000:
        raise HTTPException(413, "Configuration workbook exceeds 2 MB.")
    with SessionLocal() as db:
        cfg = latest_config(db, user.org)
        base = {**defaults(), **cfg.payload}
        version = cfg.version
    payload, errors = await run_in_threadpool(import_config, data, base)
    return {
        "valid": not errors,
        "errors": errors,
        "payload": payload,
        "expected_version": version,
        "note": "Validated draft only. Review changes and replay stored cases before publishing.",
    }
