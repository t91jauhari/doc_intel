# Per-step change inventory

## Step 1 — configuration persistence
Commit: 6df69b6 — feat(configuration): add lossless versioned publication store and offline compatibility verification.
Created: backend/app/configuration/__init__.py, store.py, verify_snapshot.py, README.md; backend/tests/test_configuration_store.py.
Modified: docs/refactor/CHECKPOINT.md, DECISIONS.md, VERIFICATION.md.
Evidence: 10 storage tests; selected regression 79 passed; 40 snapshot round trips match.

## Step 2 — PostgreSQL migration
Commit message: Add transactional configuration migrations and PostgreSQL compatibility checks.
Created: backend/app/configuration/migrate.py; backend/app/configuration/migrations/0001_publications.sql; backend/app/configuration/verify_postgres.py; backend/tests/test_configuration_migrations.py; docs/refactor/CHANGES.md.
Modified: backend/app/configuration/README.md; docs/refactor/CHECKPOINT.md; docs/refactor/MIGRATIONS.md; docs/refactor/VERIFICATION.md.
Evidence: 13 tests passed; final rollback assertion rerun 3 passed. All 40 historical revisions reconstructed twice in isolated PostgreSQL; original rows unchanged. No live migration or activation.
Git log provides the authoritative commit hash for this step.

## Step 3 — configurable identity policy
Commit message: Make customer identity checks configurable by profile and field.
Created: backend/app/configuration/identity.py (typed contracts, schema binding validation, pure matching); backend/tests/test_identity_policy.py (19 policy tests); docs/refactor/IDENTITY_CONFIGURATION.md (configuration and compatibility limits).
Modified: backend/app/grouping.py (explicit policy path with historical fallback); backend/app/domain.py (publish validation); backend/tests/test_configuration_store.py (policy round trip); docs/refactor/CHECKPOINT.md; docs/refactor/CHANGES.md; docs/refactor/VERIFICATION.md.
Verification: 42 tests passed with one baseline failure deselected; added persistence test passed separately. Failure reproduced in untouched baseline worktree, not caused by new identity policy. No live deployment.

## Step 4 — dedicated identity tables and saved-case verification
Commit message: Store identity bindings separately and verify saved-case compatibility.
Created: backend/app/configuration/migrations/0002_identity_bindings.sql; backend/app/configuration/legacy_identity_bindings.json; backend/app/configuration/shadow_identity.py.
Modified: backend/app/configuration/store.py; backend/app/configuration/README.md; backend/tests/test_configuration_store.py; backend/tests/test_configuration_migrations.py; docs/refactor/IDENTITY_CONFIGURATION.md; docs/refactor/CHECKPOINT.md; docs/refactor/MIGRATIONS.md; docs/refactor/VERIFICATION.md; docs/refactor/CHANGES.md.
Verification: 35 focused tests passed, then all 4 PostgreSQL migration tests passed after adding dedicated-table round trip. Migration 0002 applied only to restored sqe_refactor; replay no changes; 40 configuration revisions match and original cases/configurations unchanged. Shadow identity comparison: 67 cases, zero differences/errors. No live activation/push.

## Step 5 — explicit SOP membership and typed comparison foundation
Created: backend/app/configuration/rule_scope.py; backend/app/configuration/comparison.py; backend/app/configuration/shadow_scope.py; backend/tests/test_rule_contracts.py; docs/refactor/SOP_CONFIGURATION.md.
Modified: backend/app/domain.py; backend/app/transaction_flows.py; docs/refactor/CHECKPOINT.md; docs/refactor/CHANGES.md; docs/refactor/VERIFICATION.md; docs/refactor/PLAN.md.
Commit message: Add explicit SOP family membership and typed comparison contracts.
Scope: new optional rule_scope controls family membership without prefix selection; flow overrides and historical fallback retained. Pure typed comparison component added but not wired to SOP runtime. Forex evaluator dispatch prefixes, final rule tables and UI remain pending.
Step 5 verification: 44 focused tests, 18 transaction-flow/contracts tests, and one added publication test passed in their respective runs (overlapping selections). Scope comparison: 40 revisions/112 flows, zero differences. Not activated.

## Step 6 — family-rule persistence and saved comparison outcomes
Commit message: Persist SOP family memberships and verify saved comparison outcomes.
Created: backend/app/configuration/migrations/0003_family_rule_membership.sql; backend/app/configuration/shadow_comparisons.py.
Modified: backend/app/configuration/store.py; backend/app/configuration/README.md; backend/tests/test_configuration_store.py; backend/tests/test_configuration_migrations.py; docs/refactor/SOP_CONFIGURATION.md; docs/refactor/CHECKPOINT.md; docs/refactor/CHANGES.md; docs/refactor/MIGRATIONS.md; docs/refactor/VERIFICATION.md.
Verification: 51 tests passed including PostgreSQL persistence/migration. Restored migration applied once/replay empty; 40 revisions reconstructed exactly; original config/case rows unchanged. Saved comparison subset: 67 cases loaded, 61 decisive text-match outcomes checked, 0 mismatches; 5858 unsupported rule occurrences and 55 unresolved outcomes skipped explicitly. No activation or push.

## Step 7 — generic comparison runtime integration
Commit message: Integrate configurable SOP comparisons with scoring and report evidence.
Created: backend/app/configuration/generic_sop.py; backend/tests/test_generic_sop_runtime.py.
Modified: backend/app/configuration/rule_scope.py; backend/app/configuration/shadow_comparisons.py; backend/app/configuration/store.py; backend/app/document_families.py; backend/app/domain.py; backend/app/sop.py; backend/app/sop_scoring.py; backend/app/transaction_flows.py; backend/tests/test_configuration_store.py; docs/refactor/SOP_CONFIGURATION.md; docs/refactor/CHECKPOINT.md; docs/refactor/CHANGES.md; docs/refactor/VERIFICATION.md.
Behavior: optional typed generic_sop_rules, validated profiles/schema paths/families/unique IDs; explicit applicability; DATA fail for uncertain sources; standard findings/evidence; existing point scoring; Excel output; source prefixes cannot dispatch generic rules. Generic definitions persist in section entry rows. Existing rules/config versions are not converted.
Verification: existing official/Forex/scoring/flow plus initial new tests 64 passed. Final generic/storage/contracts 39 passed, including Excel rendering after fixing missing metadata in synthetic test fixture. Saved runtime outcome comparison 67 cases loaded, 61 decisive supported outcomes, zero status/eligibility/category mismatches; 5858 unsupported and 55 unresolved occurrences remain excluded. Live health ok; no activation.

## Step 8 — explicit comparison upgrade proposals
Commit message: Add explicit comparison upgrade proposals with saved-case score verification.
Created: backend/app/configuration/upgrade_comparisons.py; backend/app/configuration/shadow_upgrade.py; backend/tests/test_comparison_upgrade.py; docs/refactor/COMPARISON_UPGRADE.md.
Modified: backend/app/domain.py; backend/app/transaction_flows.py; docs/refactor/SOP_CONFIGURATION.md; docs/refactor/CHECKPOINT.md; docs/refactor/CHANGES.md; docs/refactor/VERIFICATION.md.
Verification: 45 focused tests passed, including conversion immutability/idempotency/rejection and pass/fail/missing score parity. Read-only full saved-case evaluation: 36 eligible cases, 5623 ordered findings, 144 rule conversions across case versions, zero state/eligibility/category/point/category-score differences. 18 cases blocked by current sop_review_bypass validation; 13 had no supported conversions. Private v40 draft generated for AO_SYSTEM_7 and AO_SYSTEM_13; not published or committed. Live health ok; no runtime activation.

## Step 9 — upgrade preview API and draft editor
Commit message: Add upgrade preview API and draft comparison editor.
Created: backend/app/configuration/service.py; backend/app/configuration/routes.py; backend/tests/test_configuration_upgrade_api.py; frontend/components/comparison-upgrade.tsx; frontend/AGENTS.md and frontend/CLAUDE.md (Next-generated project guidance); docs/refactor/UPGRADE_PREVIEW.md.
Modified: backend/app/main.py; frontend/app/settings/page.tsx; frontend/components/transaction-flows.tsx; frontend/lib/document-family.ts; frontend/lib/types.ts; docs/refactor/SOP_CONFIGURATION.md; docs/refactor/CHECKPOINT.md; docs/refactor/CHANGES.md; docs/refactor/VERIFICATION.md.
Additional evidence outside repository: outputs/refactor-step9/comparison-editor.png. Ignored local dependency junction/frontend .next/tsbuildinfo created for testing; generated next-env change restored.
Tests: 19 API/upgrade/runtime tests passed; TypeScript passed. Browser smoke on isolated fresh SQLite: select two Account Opening rules, preview, apply to unpublished draft, edit normalization, verify published version unchanged. No publication. Preview servers stopped; live healthy. No public push.
