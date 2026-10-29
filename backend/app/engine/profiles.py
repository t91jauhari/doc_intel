"""Document-specific schema/prompt/policy routing without changing application defaults."""

from importlib import import_module
try:
    from .account_opening.profiles import NAMES as ACCOUNT_PROFILE_NAMES, get as get_account_profile
except (ImportError, ValueError):
    from account_opening.profiles import NAMES as ACCOUNT_PROFILE_NAMES, get as get_account_profile

PROFILE_NAMES = (
    "application",
    "lld",
    "invoice",
    "valas_declaration_2",
    "valas_declaration_1",
    "ektp",
    "riplay",
) + ACCOUNT_PROFILE_NAMES


def _import_sub(mod_name):
    try:
        return import_module(f"app.engine.{mod_name}")
    except ModuleNotFoundError:
        return import_module(mod_name)


def get_profile(name):
    if name in ACCOUNT_PROFILE_NAMES:
        return get_account_profile(name)
    if name == "application":
        schema = _import_sub("schema")
        validator = _import_sub("validation").validate
        return {
            "name": name,
            "schema": schema.SCHEMA,
            "columns": schema.COLUMNS,
            "parse_prompt": schema.PARSE_PROMPT,
            "system_prompt": schema.SYSTEM_PROMPT,
            "policy": "policy.json",
            "sample": "samples/customer_transaction.pdf",
            "validate": validator,
        }
    if name == "lld":
        schema = _import_sub("lld.schema")
        validator = _import_sub("lld.validation").validate
        return {
            "name": name,
            "schema": schema.SCHEMA,
            "columns": schema.COLUMNS,
            "parse_prompt": schema.PARSE_PROMPT,
            "system_prompt": schema.SYSTEM_PROMPT,
            "policy": "lld/policy.json",
            "sample": "samples/customer_lld.pdf",
            "validate": validator,
        }
    if name == "invoice":
        schema = _import_sub("invoice.schema")
        validator = _import_sub("invoice.validation").validate
        return {
            "name": name,
            "schema": schema.SCHEMA,
            "columns": schema.COLUMNS,
            "parse_prompt": schema.PARSE_PROMPT,
            "system_prompt": schema.SYSTEM_PROMPT,
            "policy": "invoice/policy.json",
            "sample": "samples/customer_invoice.pdf",
            "validate": validator,
        }
    if name == "valas_declaration_2":
        schema = _import_sub("valas2.schema")
        validator = _import_sub("valas2.validation").validate
        return {
            "name": name,
            "schema": schema.SCHEMA,
            "columns": schema.COLUMNS,
            "parse_prompt": schema.PARSE_PROMPT,
            "system_prompt": schema.SYSTEM_PROMPT,
            "policy": "valas2/policy.json",
            "sample": "samples/customer_valas2.pdf",
            "validate": validator,
        }
    if name == "valas_declaration_1":
        schema = _import_sub("valas1.schema")
        validator = _import_sub("valas1.validation").validate
        return {
            "name": name,
            "schema": schema.SCHEMA,
            "columns": schema.COLUMNS,
            "parse_prompt": schema.PARSE_PROMPT,
            "system_prompt": schema.SYSTEM_PROMPT,
            "policy": "valas1/policy.json",
            "sample": "samples/customer_valas1.pdf",
            "validate": validator,
        }
    if name == "ektp":
        schema = _import_sub("ektp.schema")
        validator = _import_sub("ektp.validation").validate
        return {
            "name": name,
            "schema": schema.SCHEMA,
            "columns": schema.COLUMNS,
            "parse_prompt": schema.PARSE_PROMPT,
            "system_prompt": schema.SYSTEM_PROMPT,
            "policy": "ektp/policy.json",
            "sample": "samples/customer_ektp.pdf",
            "validate": validator,
        }
    if name == "riplay":
        schema = _import_sub("riplay.schema")
        validator = _import_sub("riplay.validation").validate
        return {
            "name": name,
            "schema": schema.SCHEMA,
            "columns": schema.COLUMNS,
            "parse_prompt": schema.PARSE_PROMPT,
            "system_prompt": schema.SYSTEM_PROMPT,
            "policy": "riplay/policy.json",
            "sample": "samples/customer_riplay.pdf",
            "validate": validator,
        }
    raise ValueError(f"Unknown document profile: {name}")
