# Comparison upgrade preview

Status: isolated code tested; not deployed to the existing application.

API routes:
- GET /api/config/upgrades/comparisons: administrator-only supported candidates,
  source version and family membership.
- POST /api/config/upgrades/comparisons/preview: expected_version, rule_ids and
  optional draft payload. Returns a validated proposal and basis hash. No database
  writes or publication. Stale version returns 409; invalid selection returns 422.

Configuration service holds preview/version logic; the router handles HTTP and
authorization. Existing publication endpoint remains the only publish action.

Settings > SOP rules now provides family-filtered selection, preview, and Add
upgrade to draft. Any draft/version/family change invalidates the displayed
preview. Converted comparisons remain visible with description, normalization
and enabled controls. Compared fields and applicability can now be edited through
backend-derived selections, including wrapped-text schema bindings. Flow rule selectors retain converted rules. Rule ordering is
reconciled when the draft adds/deletes checks. Multi-condition policies,
non-text operators and new-rule creation remain pending.

POST /api/config/upgrades/comparisons/fields derives text choices from the draft
family/profile schemas, enforces administrator access and expected version, and
returns supported context choices. Numeric/array and visual-region observations
are not text binding choices. A field cannot compare with itself. Visual-region
evidence is also rejected by publication validation, not just hidden in the UI.
Context choices currently use the existing backend context registry; moving that
registry into versioned database configuration remains future work.

Step 11 browser test: source changed to eKTP name, compared field opening-form
customer name, applicability customer_type=INDIVIDUAL. Read-only Test settings
accepted the draft; preview database had zero documents, so no browser outcome
coverage is claimed. Screenshot outputs/refactor-step11/field-applicability-editor.png.

Browser smoke verification used a fresh synthetic-only SQLite database on API
8100 and frontend 3100. Selected AO_SYSTEM_7/13, previewed, added to unpublished
draft and changed normalization to exact characters. Published configuration
remained version 7. No Publish action was clicked. Both preview servers were
stopped afterward; live 3000/8000 application remained healthy.

Screenshot: workspace outputs/refactor-step9/comparison-editor.png.
Backend API/runtime tests: 19 passed. Frontend TypeScript passed. Production build
was not run in this phase; the development browser routes compiled successfully.
Frontend dependency junction points to existing installed dependencies; no package
installation or live source changes. Next generated frontend AGENTS.md/CLAUDE.md
are retained; generated dev-only next-env.d.ts change was restored.
