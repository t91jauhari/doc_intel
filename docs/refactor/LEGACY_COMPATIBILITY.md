# Explicit legacy settings compatibility

Older configurations omitted seven settings now required by publication
validation. Their definitions are captured in the versioned migration input
`config_data/compatibility_defaults_v1.json`, sourced from existing default/fallback
behavior. This is draft migration data, not automatic runtime configuration.

`compatibility.propose_compatibility(payload, selected_keys)`:
- adds only explicitly selected absent keys;
- rejects unknown/duplicate selections and replacement of any existing value;
- preserves profiles, prompts, rules, customer settings and source payload;
- records a release, basis hash and exact additions;
- validates the resulting draft and never publishes it.

The release keeps `sop_review_bypass=false`. The dormant result setting is carried
with its documented value, but no review bypass is enabled. Existing invalid
administrator values must be corrected explicitly; this tool will not replace
them. Partial selections can fail validation when other required fields remain
absent. Numeric 0/1 are rejected for boolean settings.

API (administrator only):
- GET /api/config/upgrades/compatibility lists missing additions and release.
- POST /api/config/upgrades/compatibility/preview accepts expected_version,
  selected_keys and optional draft payload. Stale versions return 409. It performs
  no database writes. A dedicated compatibility editor is not yet implemented.

Read-only rehearsal:
```text
python -m app.configuration.shadow_upgrade --expected-database sqe_refactor --compatibility
```

The flag explicitly proposes missing additions in memory before supported rule
conversion, then compares against the unmodified original configuration and
saved case context/documents. It does not alter historical pins or call models.
No frontend rollout or live activation occurs in this phase.

Rehearsal result: 54 eligible cases, 7,049 ordered findings, 216 rule-conversion
occurrences across case versions, zero state/scoring differences, zero blockers.
Eighteen cases used explicit compatibility additions; thirteen other cases had
no supported conversions. Compatibility unit suite: 13 passed. API/conversion/
initial compatibility selection: 16 passed (overlapping coverage).
