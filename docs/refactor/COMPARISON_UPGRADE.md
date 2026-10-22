# Explicit comparison-rule conversion

`upgrade_comparisons.propose_upgrade(payload, selected_ids)` returns an in-memory
draft and a source fingerprint. It never changes the input, publishes a version,
alters case pins, or updates the database. The command-line interface reads a
private configuration snapshot and exclusively creates a new private draft file.

Supported conversions: unconditional Account Opening text `match` policies,
without identifier constraints, optional documents, code restrictions or companion
checks. Unknown policy settings are rejected. Already-converted IDs are reported
and not duplicated. Rule IDs, enabled states, categories, source references and
evaluation order are preserved. Schema bindings are resolved and validated, and
the entire draft must pass publication validation.

Example, with a private snapshot mounted outside the repository:

```text
python -m app.configuration.upgrade_comparisons --snapshot /private/configurations.json --organization sqe --version 40 --rule AO_SYSTEM_7 --rule AO_SYSTEM_13 --output /private/comparison-upgrade-v40.json
```

The v40 draft for those two rules has been generated privately; it is not a
published configuration. Payloads can contain private data and must not be
committed to the public repository. `rule_order` is validated to contain each
registered ID once and controls evaluation/report ordering after conversion.

`shadow_upgrade` reads the restored database in a read-only transaction. It uses
saved documents and case context, constructs proposals, compares ordered finding
IDs/status/category/eligibility and both point and category scores. Historical
configurations that fail current validation are reported as blocked, not repaired
with guessed defaults. This check does not compare prompt/model results or every
word of finding messages/evidence. Activation and UI approval remain separate.
