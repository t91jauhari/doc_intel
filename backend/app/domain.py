"""Versioned business configuration, conservative filename routing and SOP evaluation."""

import copy
import hashlib
import json
import re
import sys
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import func, select

from .db import (
    Audit,
    Base,
    Branch,
    Case,
    Config,
    Connector,
    Document,
    Inbox,
    Job,
    Report,
    SessionLocal,
    User,
    engine,
)
from .security import hash_password
from .settings import ROOT, settings

ENGINE = ROOT / "engine"
sys.path.insert(0, str(ENGINE))
from context import (  # noqa: E402 — shared engine path is initialized above.
    check_directory,
)
from profiles import PROFILE_NAMES, get_profile  # noqa: E402 — shared engine path.

LABELS = {
    "application": "Application of Transaction",
    "lld": "LLD",
    "invoice": "Underlying Invoice",
    "valas_declaration_1": "Valas 1 · Above threshold",
    "valas_declaration_2": "Valas 2 · Within threshold",
    "ektp": "eKTP",
    "riplay": "RIPLAY Document",
}
CLASSIFY_DESCRIPTIONS = {
    "riplay": "Ringkasan Informasi Produk dan Layanan (RIPLAY) Versi Personal / Personal Product Summary and Services Information. Usually four pages of bilingual benefits, risks, FX simulation and disclaimers; final-page city/date, Petugas Bank and Nasabah signature blocks, Tanggal Cetak Dokumen, bottom-right initials on each page. This is a product disclosure, not a transaction application or invoice.",
    "application": "Bank application of transaction form. Payment type, transaction type, beneficiary, remitter, SWIFT, account, currency, exchange rate, charges and signatures.",
    "lld": "Laporan Lalu Lintas Devisa (LLD) form. Penerima dana and pembayar/pengirim sections, residence status, sandi negara, categories, identification codes, financial relationship and sandi transaksi.",
    "invoice": "Underlying commercial invoice. To/customer, From/company, invoice number and dates, item table with quantity, unit price, subtotal, final total and payment bank instructions.",
    "valas_declaration_1": "Surat Pernyataan Pembelian Valas 1, Diatas Jumlah Threshold. Above-threshold declaration with identity and NPWP, tujuan/tanggal/jumlah penggunaan, sumber/tanggal/jumlah penerimaan, signature and meterai.",
    "valas_declaration_2": "Surat Pernyataan Pembelian Valas 2, Paling Banyak Sebesar Jumlah Threshold. Threshold-limited declaration of currency bought, company/individual name and address, city/date, signatory and meterai.",
    "ektp": "Indonesian electronic KTP identity card. NIK of 16 digits, name, birthplace/date, gender, blood type, RT/RW, village/district, religion, citizenship, portrait and cardholder signature.",
}
SUFFIXES = {
    "application": [
        "transaction",
        "aplikasi transaksi",
        "application",
        "application of transaction",
    ],
    "lld": ["lld"],
    "invoice": ["invoice", "underlying invoice"],
    "ektp": ["ektp", "e-ktp", "ktp"],
    "riplay": [
        "riplay",
        "riplay document",
        "riplay docume",
        # Product-named riplay forms (real ACCOP batches)
        "form riplay",
        "riplay payroll",
        "riplay gold",
        "riplay diamond",
        "riplay simas gold",
        "riplay pemrek diamond",
        "riplay pemrek gold",
        "riplay pemrek tabunganku",
        "riplay tabunganku",
    ],
    "valas_declaration_1": [
        "valas1",
        "valas 1",
        "surat pernyataan pembelian valas 1 (diatas jumlah threshold)",
    ],
    "valas_declaration_2": [
        "valas2",
        "valas 2",
        "surat pernyataan pembelian valas 2 (paling banyak sebesar jumlah threshold)",
    ],
}


from account_opening.profiles import REFERENCE as ACCOUNT_REFERENCE

for _name, _definition in ACCOUNT_REFERENCE["profiles"].items():
    LABELS[_name] = _definition["label"]
    CLASSIFY_DESCRIPTIONS[_name] = (
        "Account Opening: "
        + _definition["label"]
        + ". Fields: "
        + ", ".join(f["label"] for f in _definition["fields"][:6])
    )
    SUFFIXES[_name] = [_name, _definition["label"]]
SUFFIXES["join_visit"] += ["joint visit", "join visit", "visiting"]
SUFFIXES["edd"] += ["eed", "enhanced due diligence"]
SUFFIXES["account_opening_form"] += [
    "pembukaan rekening",
    "account opening",
    "opening form",
    "formulir pembukaan rekening",
    # Abbreviated / product-named opening forms (real ACCOP batches)
    "pembukaan rek",
    "pemrek tabunganku",
    "tabunganku",
]
SUFFIXES["signature_difference"] += ["beda tanda tangan", "beda tandatangan"]
SUFFIXES["company_reference"] += [
    "referensi perusahaan",
    "surat referensi",
    "company reference",
]

# ---------------------------------------------------------------------------
# Phase 1 — Enhanced Grouping Logic & Externalized Message Templates (§3.1, §3.3)
# ---------------------------------------------------------------------------

GROUPING_PREFIXES = [
    # English
    "forex",
    "account opening",
    "account open",
    # Indonesian — full
    "pembukaan rekening",
    "pembukaan tabungan",
    "formulir pembukaan rekening",
    # Indonesian — abbreviated
    "pemrek tab",
    "pemrek",
    "buka rekening",
    "buka rek",
    "tab",
    "rek",
]

SUFFIX_ALIASES = {
    # abbreviation → canonical suffix already in SUFFIXES
    "rek": "pembukaan rekening",
    "pemrek": "pembukaan rekening",
    "pemrek tab": "pembukaan rekening",
    "buka rek": "pembukaan rekening",
    "tab": "pembukaan tabungan",
    "ktp": "ektp",
    "e-ktp": "ektp",
    "applikasi": "aplikasi transaksi",
    "aplikasi": "aplikasi transaksi",
    "slip aplikasi": "aplikasi transaksi",
    "inv": "invoice",
    "faktur": "invoice",
    "lld form": "lld",
    "laporan lalu lintas devisa": "lld",
}

SOP_MESSAGE_TEMPLATES = {
    # account_opening_sop.py
    "ao.opening_form_missing": "Opening form missing or ambiguous.",
    "ao.wic_survey_applicability": "WIC survey applicability requires an audited document-based decision; no survey field schema supplied.",
    "ao.conditional_unresolved": "Conditional applicability is unresolved.",
    "ao.combined_birth_review": "Combined birth text needs exact source comparison; formatting may differ.",
    "ao.source_missing_ambiguous": "Source document missing or ambiguous.",
    "ao.manual_evidence_review": "Uploaded evidence must be reviewed; no authenticity, external specimen or physical-inventory verification is inferred.",
    "ao.supporting_source_review": "Supporting source uncertainty requires review.",
    "ao.source_uncertainty_review": "Source uncertainty requires review.",
    "ao.applicability_context": "Applicability needs documented case context.",
    # sop.py
    "sop.applicability_context": "Applicability needs documented case context.",
    "sop.missing_ambiguous_ref": "Missing or ambiguous document reference.",
    "sop.unreadable_values": "Unreadable or incompatible extracted values.",
    "sop.low_confidence_source": "Low-confidence/unreadable source needs correction or reviewed evidence.",
    # grouping.py
    "grouping.manual_confirmed": "Customer assignment confirmed by user.",
    "grouping.one_compatible": "One compatible customer in this batch.",
    "grouping.normalized_match": "Normalized customer name matched.",
    "grouping.similar_spellings": "Similar spellings need confirmation; keep separate or choose one customer.",
    "grouping.multiple_compatible": "Multiple compatible customers; choose the correct customer.",
    "grouping.missing_name": "Customer name is missing; assign this document.",
    "grouping.identity_conflict": "Extracted customer names disagree. Review document grouping; assignments were retained.",
    "grouping.expected_compatible": "Compatible customer identities within one case.",
    # case_processing.py
    "processing.incomplete": "Document processing incomplete.",
    "processing.native_quality": "Native document quality check",
    "processing.required_missing": "Required document missing.",
    # domain.py route()
    "route.unassigned_reason": "No approved filename label. Content classification still pending.",
    "route.filename_reason": "Recognized document label; content verification still pending.",
}


def serial(value):
    return json.loads(
        json.dumps(
            value,
            default=lambda x: format(x, "f") if isinstance(x, Decimal) else str(x),
        )
    )


def audit(db, org, actor, event, branch_id=None, case_id=None, **details):
    db.add(
        Audit(
            org=org,
            actor=actor,
            event=event,
            branch_id=branch_id,
            case_id=case_id,
            details=serial(details),
        )
    )


def default_config():
    from .spider_provider import DEFAULT_INSTRUCTION

    from .spatial_grounding import append_instruction
    from .forex_sop import DEFAULT_POLICY
    profiles = {}
    for name in PROFILE_NAMES:
        p = get_profile(name)
        profiles[name] = {
            "label": LABELS[name],
            "classification_description": CLASSIFY_DESCRIPTIONS[name],
            "parse_prompt": p["parse_prompt"],
            "system_prompt": p["system_prompt"],
            "system_instruction": append_instruction(DEFAULT_INSTRUCTION),
            "policy": json.loads((ENGINE / p["policy"]).read_text(encoding="utf-8")),
            "suffixes": SUFFIXES[name],
            "columns": p["columns"],
            "schema": copy.deepcopy(p["schema"]),
            "schema_version": hashlib.sha256(
                json.dumps(p["schema"], sort_keys=True).encode()
            ).hexdigest(),
        }
    from .sop import defaults

    return {
        **defaults(),
        "customer_aliases": {},
        "provider": "spider-ai",
        "parse_tier": "agentic_plus",
        "extract_tier": "agentic_plus",
        "parse_version": "latest",
        "extract_version": "latest",
        "maker_checker": False,
        "profiles": profiles,
        "name_directory": json.loads(
            (ENGINE / "name_directory.json").read_text(encoding="utf-8")
        ),
        "templates": {
            "forex": {
                "label": "Forex starter · 3 required documents",
                "required": ["application", "lld", "invoice"],
            },
            "custom": {"label": "Flexible case", "required": []},
        },
        "classification_threshold": 0.85,
        "rules": [],
        "report_title": "Kertas Kerja · Document & SOP Review",
        # Phase 1 — Enhanced Grouping Logic & Externalized Message Templates (§3.1, §3.3)
        "grouping_prefixes": list(GROUPING_PREFIXES),
        "suffix_aliases": dict(SUFFIX_ALIASES),
        "sop_message_templates": dict(SOP_MESSAGE_TEMPLATES),
        "forex_sop_policy": copy.deepcopy(DEFAULT_POLICY),
        # Phase 2 — Configurable SOP Review Bypass (§3.2)
        "sop_review_bypass": False,
        "sop_review_bypass_result": "PASS",
        # Phase 3 — Multi-Page Sequential Extraction (§3.5)
        "sequential_page_extraction": True,
        "cross_page_reference": True,
    }


def validate_config(payload):
    if "rule_scope" in payload:
        from .configuration.rule_scope import validate_rule_scope

        validate_rule_scope(payload)
    if "identity_policy" in payload:
        from .configuration.identity import IdentityPolicy, validate_bindings

        validate_bindings(IdentityPolicy.model_validate(payload["identity_policy"]), payload["profiles"])
    from .forex_sop import validate_policy
    validate_policy(payload)
    from .schema_descriptions import validate_profile_schema, validate_descriptions

    base = default_config()
    variants = payload.get("profile_variants", {})
    if not isinstance(variants, dict) or set(variants) - set(PROFILE_NAMES):
        raise ValueError("Invalid profile variant document types.")
    for name, bank in variants.items():
        if not isinstance(bank, dict) or len(bank) > 30:
            raise ValueError("Invalid profile variant collection.")
        for key, variant in bank.items():
            if (
                not isinstance(key, str)
                or not isinstance(variant, dict)
                or not isinstance(variant.get("name"), str)
                or not variant["name"].strip()
            ):
                raise ValueError("Profile variants require a name.")
            candidate = copy.deepcopy(base)
            candidate["profiles"][name] = variant["profile"]
            validate_config(candidate)
    if payload.get("provider") not in {"spider-ai", "llama", "fixture"}:
        raise ValueError("Select spider-ai, llama or fixture provider.")
    if payload["provider"] == "fixture" and settings.environment != "development":
        raise ValueError("Fixture mode is development-only.")
    # Phase 2 — Configurable SOP Review Bypass (§3.2.1)
    if payload.get("sop_review_bypass") not in (True, False):
        raise ValueError("sop_review_bypass must be true or false.")
    if payload.get("sop_review_bypass_result") not in {"PASS", "REVIEW", "NOT_APPLICABLE"}:
        raise ValueError(
            "sop_review_bypass_result must be PASS, REVIEW, or NOT_APPLICABLE."
        )
    # Phase 1 — Grouping configuration (§3.1) and message templates (§3.3)
    prefixes = payload.get("grouping_prefixes")
    if not isinstance(prefixes, list) or not all(
        isinstance(p, str) and p.strip() for p in prefixes
    ) or len(prefixes) > 200:
        raise ValueError("grouping_prefixes must be a list of non-empty strings.")
    aliases = payload.get("suffix_aliases")
    if not isinstance(aliases, dict) or not all(
        isinstance(k, str) and k.strip() and isinstance(v, str) and v.strip()
        for k, v in aliases.items()
    ) or len(aliases) > 500:
        raise ValueError("suffix_aliases must map non-empty strings to non-empty strings.")
    templates = payload.get("sop_message_templates")
    if not isinstance(templates, dict) or not all(
        isinstance(k, str) and k.strip() and isinstance(v, str)
        for k, v in templates.items()
    ) or len(templates) > 500:
        raise ValueError("sop_message_templates must map keys to message strings.")
    # Phase 3 — Sequential extraction settings (§3.5.4)
    for flag in ["sequential_page_extraction", "cross_page_reference"]:
        if payload.get(flag) not in (True, False):
            raise ValueError(f"{flag} must be true or false.")
    for tier in ["parse_tier", "extract_tier"]:
        if payload.get(tier) not in {"agentic", "agentic_plus", "cost_effective"}:
            raise ValueError("Invalid processing tier.")
    if set(payload.get("profiles", {})) != set(PROFILE_NAMES):
        raise ValueError("All supported profile configurations are required.")
    for name, p in payload["profiles"].items():
        if "system_instruction" in p and (
            not isinstance(p["system_instruction"], str)
            or not 10 <= len(p["system_instruction"].strip()) <= 30000
        ):
            raise ValueError(
                f"{name}: System Instruction must contain 10–30000 characters."
            )
        if name in ACCOUNT_REFERENCE["profiles"]:
            from account_opening.profiles import validate_policy

            validate_policy(name, p.get("policy", {}))
        if name == "ektp":
            from .enum_aliases import validate_aliases

            validate_aliases(p.get("policy", {}))
        validate_profile_schema(p, base['profiles'][name], payload['provider'])
        if "schema" in p:
            validate_descriptions(p["schema"], name)
        if (
            "schema_version" in p
            and not re.fullmatch(r'[a-f0-9]{64}', str(p['schema_version']))
        ):
            raise ValueError(f"{name}: invalid schema version.")
        if not isinstance(p.get("policy"), dict) or not set(
            base["profiles"][name]["policy"]
        ).difference({"enum_aliases", "enum_raw_fallback_fields"}).issubset(
            p["policy"]
        ):
            raise ValueError(f"{name}: missing policy keys.")
        if not all(
            isinstance(p.get(x), str) and p[x].strip()
            for x in ["parse_prompt", "system_prompt"]
        ):
            raise ValueError(f"{name}: prompts cannot be blank.")
        if (
            not isinstance(p.get("classification_description"), str)
            or not p["classification_description"].strip()
        ):
            raise ValueError(f"{name}: classification description is required.")
        if not isinstance(p.get("suffixes"), list) or not all(
            isinstance(x, str) and x.strip() for x in p["suffixes"]
        ):
            raise ValueError(f"{name}: invalid suffixes.")
        for key, expected in base["profiles"][name]["policy"].items():
            actual = p["policy"][key]
            if expected is not None:
                valid = isinstance(actual, type(expected))
                if isinstance(expected, float):
                    valid = isinstance(actual, (int, float)) and not isinstance(
                        actual, bool
                    )
                if isinstance(expected, int) and not isinstance(expected, bool):
                    valid = isinstance(actual, int) and not isinstance(actual, bool)
                if not valid:
                    raise ValueError(f"{name}: policy.{key} has an invalid type.")
    aliases = payload.get("customer_aliases", {})
    if not isinstance(aliases, dict) or any(
        not isinstance(k, str)
        or not k.strip()
        or not isinstance(v, str)
        or not v.strip()
        for k, v in aliases.items()
    ):
        raise ValueError(
            "Customer aliases must map non-empty labels to canonical names."
        )
    if len({k.strip().casefold() for k in aliases}) != len(aliases):
        raise ValueError("Duplicate normalized customer alias.")
    check_directory(payload.get("name_directory", {}))
    if not isinstance(payload.get("maker_checker"), bool):
        raise ValueError("maker_checker must be boolean.")
    if (
        not isinstance(payload.get("classification_threshold"), (int, float))
        or not 0 <= payload["classification_threshold"] <= 1
    ):
        raise ValueError("Classification threshold must be between zero and one.")
    from .transaction_flows import validate_flows

    validate_flows(payload)
    if (
        not isinstance(payload.get("report_title"), str)
        or not payload["report_title"].strip()
        or len(payload["report_title"]) > 200
    ):
        raise ValueError("Report title must contain 1–200 characters.")
    for key in ("parse_version", "extract_version"):
        if not isinstance(payload.get(key), str) or not payload[key].strip():
            raise ValueError("Provider versions must not be blank.")
    for template in payload["templates"].values():
        if not set(template.get("required", [])).issubset(PROFILE_NAMES):
            raise ValueError("Template includes an unknown document type.")
    ids = set()
    for rule in payload.get("rules", []):
        if rule.get("id") in ids or not rule.get("id"):
            raise ValueError("Rule IDs must be unique.")
        ids.add(rule["id"])
        if rule.get("operator") not in {
            "required",
            "equals",
            "enum",
            "positive",
            "match",
        }:
            raise ValueError("Unsupported SOP operator.")
        if rule.get("severity") not in {"FAIL", "REVIEW"}:
            raise ValueError("Rule severity must be FAIL or REVIEW.")
        if not rule.get("path") or rule["path"].split(".")[0] not in PROFILE_NAMES:
            raise ValueError("Rule paths start with a document profile.")
        if rule["operator"] == "match" and (
            not rule.get("other_path")
            or rule["other_path"].split(".")[0] not in PROFILE_NAMES
        ):
            raise ValueError("A match rule requires another profile.field path.")
    from .sop import validate_business

    validate_business(payload)
    return payload


def latest_config(db, org):
    return db.scalar(
        select(Config).where(Config.org == org).order_by(Config.version.desc()).limit(1)
    )


def seed():
    import os

    if settings.environment != "development":
        return
    Base.metadata.create_all(engine)
    with SessionLocal.begin() as db:
        org = os.getenv("DEV_ORGANIZATION", "sqe")
        email = os.getenv("DEV_EMAIL", "sqe@bic.local").lower()
        if not db.scalar(select(User).where(User.org == org, User.email == email)):
            password = os.getenv("DEV_PASSWORD")
            if not password:
                raise RuntimeError(
                    "Set DEV_PASSWORD through the development initialization script."
                )
            branch = Branch(org=org, code="HQ", name="SQE · Development Branch")
            db.add(branch)
            db.flush()
            user = User(
                org=org,
                email=email,
                name="SQE Administrator",
                password_hash=hash_password(password),
                role="bank_admin",
                branches=[branch.id],
            )
            db.add(user)
            db.flush()
            cfg = Config(
                org=org, version=1, payload=default_config(), published_by=user.id
            )
            db.add(cfg)
            db.add(Connector(org=org, encrypted="", options={}))
            audit(db, org, user.id, "development.bootstrap", branch.id, email=email)

        upgrade_profiles(db, org)


def upgrade_profiles(db, org):
    """Publish additions as a new version; existing case configurations stay immutable."""
    previous = latest_config(db, org)
    if previous is None:
        return False
    defaults = default_config()
    missing = set(defaults["profiles"]) - set(previous.payload["profiles"])
    automation_missing = "workflow" not in previous.payload
    riplay_update = previous.payload.get("profiles", {}).get("riplay", {}).get(
        "policy", {}
    ).get("required_initial_pages") != [1, 2, 3]
    # Phase 1/2/3 — detect missing enhancement fields for migration
    enhancement_missing = any(
        key not in previous.payload
        for key in (
            "grouping_prefixes",
            "suffix_aliases",
            "sop_message_templates",
            "sop_review_bypass",
            "sop_review_bypass_result",
            "sequential_page_extraction",
            "cross_page_reference",
        )
    )
    # Existing profiles must pick up new default suffixes added in code
    # (e.g. product-named riplay forms). Merge-only: user-suffixes preserved.
    suffix_missing = any(
        name in previous.payload.get("profiles", {})
        and not set(defaults["profiles"][name]["suffixes"])
        <= set(previous.payload["profiles"][name].get("suffixes", []))
        for name in defaults["profiles"]
    )
    if (
        not missing
        and not automation_missing
        and not riplay_update
        and not enhancement_missing
        and not suffix_missing
    ):
        return False
    payload = copy.deepcopy(previous.payload)
    if automation_missing:
        from .sop import defaults as automation_defaults

        payload.update(automation_defaults())
        for name in payload["profiles"]:
            payload["profiles"][name]["schema"] = defaults["profiles"][name]["schema"]
            payload["profiles"][name]["schema_version"] = defaults["profiles"][name][
                "schema_version"
            ]
    if riplay_update and "riplay" in payload["profiles"]:
        rp = payload["profiles"]["riplay"]
        rp["policy"] = {**rp["policy"], "required_initial_pages": [1, 2, 3]}
        rp["schema"] = defaults["profiles"]["riplay"]["schema"]
        rp["schema_version"] = defaults["profiles"]["riplay"]["schema_version"]
        clarification = "\nRIPLAY page-rule clarification overrides any older footer instruction: require bottom-right customer initials on pages 1, 2 and 3 only. Page 4 contains the main signing fields and needs no separate footer initial."
        rp["system_prompt"] += clarification
        rp["parse_prompt"] += clarification
    payload.setdefault("customer_aliases", {})
    for name in missing:
        payload["profiles"][name] = defaults["profiles"][name]
    # Merge new default suffixes into existing profiles (union, order preserved,
    # user-added suffixes untouched) so product-named forms keep grouping.
    for name, profile in payload["profiles"].items():
        if name in defaults["profiles"]:
            for suffix in defaults["profiles"][name]["suffixes"]:
                if suffix not in profile["suffixes"]:
                    profile["suffixes"] = list(profile["suffixes"]) + [suffix]
    # Phase 1/2/3 — backfill enhancement fields with defaults (existing values preserved)
    payload.setdefault("grouping_prefixes", list(GROUPING_PREFIXES))
    payload.setdefault("suffix_aliases", dict(SUFFIX_ALIASES))
    payload.setdefault("sop_message_templates", dict(SOP_MESSAGE_TEMPLATES))
    payload.setdefault("sop_review_bypass", False)
    payload.setdefault("sop_review_bypass_result", "PASS")
    payload.setdefault("sequential_page_extraction", True)
    payload.setdefault("cross_page_reference", True)
    db.add(
        Config(
            org=org,
            version=previous.version + 1,
            payload=payload,
            published_by="system.profile-upgrade",
        )
    )
    audit(
        db,
        org,
        "system",
        "configuration.profiles_added",
        None,
        profiles=sorted(missing),
    )
    return True


def riplay_identity_findings(documents, cfg):
    riplays = [
        d for d in documents if d.doc_type == "riplay" and d.status == "COMPLETED"
    ]
    if not riplays or not cfg["profiles"].get("riplay", {}).get("policy", {}).get(
        "require_identity_match", True
    ):
        return []
    identities = [
        d for d in documents if d.doc_type == "ektp" and d.status == "COMPLETED"
    ]
    findings = []
    for doc in riplays:
        actual = doc.normalized.get("customer_name")
        expected = (
            identities[0].normalized.get("name") if len(identities) == 1 else None
        )
        valid_reference = (
            len(identities) == 1
            and identities[0].validation.get("fields", {}).get("name", {}).get("status")
            == "PASS"
        )
        result = "REVIEW"
        if actual and expected and valid_reference:

            def normalize(value):
                return " ".join(str(value).split()).casefold()

            result = "PASS" if normalize(actual) == normalize(expected) else "FAIL"
        findings.append(
            {
                "rule_id": "riplay.customer_name_vs_ektp.name",
                "field": "riplay.customer_name",
                "actual": actual,
                "expected": expected,
                "result": result,
                "message": "RIPLAY customer name must match one readable eKTP name in this case; missing or ambiguous reference needs review.",
                "evidence": {
                    "document_id": doc.id,
                    "reference_document_ids": [d.id for d in identities],
                    "match_method": "case_and_whitespace_insensitive_exact",
                },
            }
        )
    return findings


def route(filename, cfg):
    templates = cfg.get("sop_message_templates", {})
    stem = re.sub(r"^(?:\(Compressed\)\s*)+", "", Path(filename).stem, flags=re.I)
    stem = re.sub(r"[\[\]()]", " ", stem).strip()
    # Phase 1 §3.1.1 — Configurable prefix stripping (was hardcoded forex|account opening)
    prefixes = cfg.get("grouping_prefixes", GROUPING_PREFIXES)
    if prefixes:
        prefix_pattern = r"^(?:" + "|".join(re.escape(p) for p in prefixes) + r")[_\s.-]+"
        stem = re.sub(prefix_pattern, "", stem, flags=re.I)
    # Signing/scan status markers are not part of the customer name nor of any
    # document label (e.g. "Form Pembukaan Rek_signed", "- KTP signed").
    stem = re.sub(
        r"[_\s.-]+(?:signed|unsigned|scanned|scan|ttd|final|copy)+(?=[_\s.-]|$)",
        "",
        stem,
        flags=re.I,
    )
    labels = {
        "form riplay": "riplay",
        "riplay": "riplay",
        "form lld": "lld",
        "lld": "lld",
        "slip aplikasi transaksi": "application",
        "aplikasi transaksi": "application",
        "dokumen underlying": "invoice",
        "invoice": "invoice",
        "ektp": "ektp",
        "surat pernyataan pembelian valas": "unknown",
    }
    for name, profile in cfg["profiles"].items():
        for suffix in profile["suffixes"]:
            labels[suffix] = name
    # Phase 1 §3.1.2 — Inject suffix aliases so abbreviations resolve to canonical profiles
    for alias, canonical in cfg.get("suffix_aliases", SUFFIX_ALIASES).items():
        if canonical in labels:
            labels[alias] = labels[canonical]
    patterns = []
    for label, kind in sorted(labels.items(), key=lambda x: -len(x[0])):
        words = re.findall(r"[^\W_]+", label, re.UNICODE)
        if words:
            patterns.append((r"[_\s.-]+".join(re.escape(w) for w in words), kind))
    matched = []
    customer = stem
    # Remove known labels at either edge; preserve all interior customer tokens.
    for _ in range(3):
        found = False
        for pattern, kind in patterns:
            if re.fullmatch(pattern, customer, re.I):
                customer = ""
                matched.append(kind)
                found = True
                break
            prefix = re.match(pattern + r"[_\s.-]+(.+)$", customer, re.I)
            suffix = re.search(r"[_\s.-]+" + pattern + r"$", customer, re.I)
            if prefix:
                customer = prefix.group(1).strip(" _-")
            elif suffix:
                customer = customer[: suffix.start()].strip(" _-")
            else:
                continue
            matched.append(kind)
            found = True
            break
        if not found or not customer:
            break
    # Phase 1 §3.1.3 — Fuzzy label matching fallback when exact patterns fail
    if not matched and customer:
        from difflib import SequenceMatcher

        best_label, best_ratio = None, 0.0
        for label, kind in labels.items():
            ratio = SequenceMatcher(None, customer.lower(), label).ratio()
            if ratio > best_ratio:
                best_label, best_ratio = kind, ratio
        if best_ratio >= 0.80:
            matched.append(best_label)
    customer = re.sub(r"[_\s]+", " ", customer).strip(" -")
    # Strip residual connector words (e.g. "Artha Milani-Form" after removing
    # the "EDD" label from "Artha Milani-Form EDD"). A customer name never
    # ends/starts with these generic document words.
    customer = re.sub(
        r"[\s_-]+(?:form|formulir|dokumen|document|doc)$", "", customer, flags=re.I
    )
    customer = re.sub(
        r"^(?:form|formulir|dokumen|document|doc)[\s_-]+", "", customer, flags=re.I
    ).strip(" -")
    if not matched:
        return (
            "unknown",
            customer,
            {
                "method": "unassigned",
                "reason": templates.get(
                    "route.unassigned_reason",
                    SOP_MESSAGE_TEMPLATES["route.unassigned_reason"],
                ),
            },
        )
    hint = matched[0] if len(set(matched)) == 1 else "unknown"
    return (
        hint,
        customer,
        {
            "method": "filename",
            "reason": templates.get(
                "route.filename_reason",
                SOP_MESSAGE_TEMPLATES["route.filename_reason"],
            ),
            "confirmed": False,
        },
    )


def enqueue(db, doc, action="process"):
    running = db.scalar(
        select(Job).where(
            Job.document_id == doc.id,
            Job.status.in_(["QUEUED", "DISPATCHED", "RUNNING"]),
        )
    )
    if running:
        return running
    doc.status = "QUEUED"
    doc.error = ""
    case = db.get(Case, doc.case_id)
    case.status = "QUEUED"
    case.updated_at = time.time()
    job = Job(org=doc.org, branch_id=doc.branch_id, document_id=doc.id, action=action)
    db.add(job)
    return job


def extract_path(documents, path):
    parts = path.split(".")
    documents = [
        d for d in documents if d.doc_type == parts[0] and d.status == "COMPLETED"
    ]
    if len(documents) != 1:
        return None
    value = documents[0].normalized
    for part in parts[1:]:
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def evaluate_rules(documents, rules):
    findings = []
    for rule in rules:
        actual = extract_path(documents, rule["path"])
        expected = rule.get("value")
        op = rule["operator"]
        result = "PASS"
        if op == "required":
            valid = actual not in (None, "", [], {})
        elif actual is None:
            valid = False
            result = "REVIEW"
        elif op == "equals":
            valid = actual == expected
        elif op == "enum":
            valid = actual in expected if isinstance(expected, list) else False
        elif op == "positive":
            try:
                valid = Decimal(str(actual)) > 0
            except InvalidOperation:
                valid = False
        else:
            expected = extract_path(documents, rule["other_path"])
            if expected is None:
                result = "REVIEW"
                valid = False
            else:
                a, b = str(actual).strip().casefold(), str(expected).strip().casefold()
                valid = a == b
        if not valid and result != "REVIEW":
            result = rule["severity"]
        findings.append(
            {
                "rule_id": rule["id"],
                "field": rule["path"],
                "actual": actual,
                "expected": expected,
                "result": result,
                "message": rule.get("label", rule["id"]),
                "evidence": {"path": rule["path"]},
            }
        )
    return findings


def refresh_case(db, case_id):
    # Serialize report creation per case on PostgreSQL.
    case = db.scalar(select(Case).where(Case.id == case_id).with_for_update())
    docs = db.scalars(
        select(Document)
        .where(Document.case_id == case_id)
        .order_by(Document.created_at)
    ).all()
    cfg_record = db.get(Config, case.config_id)
    cfg = cfg_record.payload
    if "workflow" in cfg:
        from .case_processing import queue_case

        return queue_case(db, case_id)
    required = cfg["templates"][case.template]["required"]
    present = {d.doc_type for d in docs}
    missing = [x for x in required if x not in present]
    findings = riplay_identity_findings(docs, cfg)
    if riplay_update and "riplay" in payload["profiles"]:
        rp = payload["profiles"]["riplay"]
        rp["policy"] = {**rp["policy"], "required_initial_pages": [1, 2, 3]}
        rp["schema"] = defaults["profiles"]["riplay"]["schema"]
        rp["schema_version"] = defaults["profiles"]["riplay"]["schema_version"]
        clarification = "\nRIPLAY page-rule clarification overrides any older footer instruction: require bottom-right customer initials on pages 1, 2 and 3 only. Page 4 contains the main signing fields and needs no separate footer initial."
        rp["system_prompt"] += clarification
        rp["parse_prompt"] += clarification
    payload.setdefault("customer_aliases", {})
    for name in missing:
        findings.append(
            {
                "rule_id": "case.required_document",
                "field": name,
                "result": "FAIL",
                "actual": None,
                "expected": "Document present",
                "message": f"Missing {LABELS[name]}",
                "evidence": {},
            }
        )
    for name in set(d.doc_type for d in docs if d.doc_type != "unknown"):
        if sum(d.doc_type == name for d in docs) > 1:
            findings.append(
                {
                    "rule_id": "case.duplicate_type",
                    "field": name,
                    "result": "REVIEW",
                    "message": "Multiple documents of this type. Review case membership.",
                    "evidence": {},
                }
            )
    for d in docs:
        if d.status == "ERROR":
            findings.append(
                {
                    "rule_id": "processing.error",
                    "field": d.filename,
                    "result": "REVIEW",
                    "message": d.error,
                    "evidence": {"document_id": d.id},
                }
            )
        if d.doc_type == "unknown":
            findings.append(
                {
                    "rule_id": "case.unassigned",
                    "field": d.filename,
                    "result": "REVIEW",
                    "message": "Document type and case membership need review.",
                    "evidence": {"document_id": d.id},
                }
            )
        for key, field in d.validation.get("fields", {}).items():
            for issue in field.get("issues", []):
                findings.append(
                    {
                        "rule_id": issue["code"],
                        "field": f"{d.doc_type}.{key}",
                        "result": issue.get("severity", "REVIEW"),
                        "actual": field.get("normalized_value"),
                        "message": issue["code"].replace("_", " ").capitalize(),
                        "evidence": {
                            "document_id": d.id,
                            "metadata": field.get("metadata", {}),
                        },
                    }
                )
    findings += evaluate_rules(docs, cfg["rules"])
    active = any(
        d.status
        in {"QUEUED", "CLASSIFYING", "UPLOADING", "PARSING", "EXTRACTING", "VALIDATING"}
        for d in docs
    )
    if active:
        case.status = "PROCESSING"
    elif any(d.status == "ERROR" for d in docs):
        case.status = "PROCESSING_ERROR"
    elif missing:
        case.status = "WAITING_DOCUMENTS"
    elif any(d.status == "NEEDS_CLASSIFICATION" for d in docs):
        case.status = "NEEDS_REVIEW"
    else:
        case.status = (
            "NEEDS_REVIEW"
            if any(x["result"] in {"FAIL", "REVIEW"} for x in findings)
            else "READY"
        )
    case.validation_status = (
        "FAIL"
        if any(x["result"] == "FAIL" for x in findings)
        else "REVIEW"
        if any(x["result"] == "REVIEW" for x in findings)
        else "PENDING"
        if active
        else "PASS"
    )
    case.updated_at = time.time()
    snapshot = {
        "case_id": case.id,
        "reference": case.reference,
        "customer": case.customer,
        "branch_id": case.branch_id,
        "organization": case.org,
        "status": case.status,
        "validation_status": case.validation_status,
        "config_version": cfg_record.version,
        "config_id": cfg_record.id,
        "report_title": cfg["report_title"],
        "provider": cfg["provider"],
        "missing": missing,
        "findings": serial(findings),
        "documents": [
            {
                "id": d.id,
                "filename": d.filename,
                "sha256": d.sha256,
                "doc_type": d.doc_type,
                "status": d.status,
                "classification": d.classification,
                "raw": d.raw,
                "normalized": d.normalized,
                "overrides": d.overrides,
                "validation": d.validation,
                "provider_state": d.provider_state,
            }
            for d in docs
        ],
    }
    fingerprint = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, default=str).encode()
    ).hexdigest()
    report = db.scalar(
        select(Report).where(
            Report.case_id == case.id, Report.fingerprint == fingerprint
        )
    )
    if not active and not report:
        version = (
            db.scalar(select(func.max(Report.version)).where(Report.case_id == case.id))
            or 0
        ) + 1
        snapshot["generated_at"] = time.time()
        report = Report(
            org=case.org,
            branch_id=case.branch_id,
            case_id=case.id,
            version=version,
            fingerprint=fingerprint,
            snapshot=snapshot,
        )
        db.add(report)
        db.flush()
        from .reporting import persist_report

        # An unavailable store must not roll back the recorded processing error.
        # Error-case artifacts are materialized when downloaded after recovery.
        if case.status != "PROCESSING_ERROR":
            persist_report(report)
        audit(
            db,
            case.org,
            "worker",
            "report.draft_generated",
            case.branch_id,
            case.id,
            version=version,
        )
    inbox = db.scalar(select(Inbox).where(Inbox.key == case.id))
    actionable = case.status in {
        "WAITING_DOCUMENTS",
        "PROCESSING_ERROR",
        "NEEDS_REVIEW",
        "READY",
    }
    title = f"{case.customer} · " + {
        "WAITING_DOCUMENTS": "Missing documents",
        "PROCESSING_ERROR": "Processing needs attention",
        "NEEDS_REVIEW": "Review findings",
        "READY": "Report ready for release",
    }.get(case.status, "Processing")
    body = f"{len(findings)} findings · {len(missing)} missing documents · {case.validation_status}"
    if not inbox and actionable:
        db.add(
            Inbox(
                org=case.org,
                branch_id=case.branch_id,
                case_id=case.id,
                key=case.id,
                title=title,
                body=body,
                severity="action",
                resolved=False,
            )
        )
    elif inbox:
        if inbox.title != title or inbox.body != body:
            inbox.read_by = []
        inbox.title = title
        inbox.body = body
        inbox.resolved = not actionable
    return snapshot
