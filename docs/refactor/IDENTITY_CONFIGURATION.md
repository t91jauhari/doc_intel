# Configurable customer identity checks

Status: implemented in the isolated refactor; not activated in live configuration.

An optional `identity_policy` in a published payload controls which completed
documents contribute customer names and how those names are compared:

```json
{
  "identity_policy": {
    "comparison": "compatible_initials",
    "bindings": [
      {"profile": "custom_profile", "field_path": "holder.name"},
      {"profile": "wrapped_profile", "field_path": "customer_name", "schema_path": "customer_name.raw"}
    ]
  }
}
```

`field_path` addresses normalized extraction results. `schema_path` is optional
and identifies the same field or its wrapped scalar in the extraction schema.
The bound schema value must be string or nullable string. Profile existence,
field existence, duplicate bindings, unsupported modes, unknown settings and
non-customer roles are rejected. Only one identity binding per profile is
supported in this first version. Array traversal is not supported.

`exact_tokens` compares complete normalized token sequences. The compatibility
mode retains existing ordered-initial matching and requires a shared full token;
initials alone do not establish identity. Missing/unreadable values do not
establish a conflict or prove consistency. Beneficiaries, suppliers and signers
are not read unless an administrator incorrectly binds their fields: semantic
field-role correctness still requires configuration review.

Absent policy retains historical mapping and matching. An explicit empty binding
list disables this identity conflict check. Existing findings, evidence structure
and scoring eligibility are preserved. This does not change filename-based bulk
group planning, SOP name comparison, extraction schemas or prompts.

New policies persist in dedicated publication-scoped identity policy and binding
tables after migration 0002. Historical publications without this policy remain
unchanged. An administrator UI is pending.
No startup seeding changes historical configurations.

The read-only `shadow_identity` command compares historical behavior against the
declarative compatibility proposal in `legacy_identity_bindings.json`. That file
is migration input, not a new runtime default. The proposal validates plain versus
wrapped historical text schemas; it does not publish configuration. The restored
67-case snapshot produced zero differences and zero configuration errors.
