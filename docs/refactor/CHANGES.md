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

## Step 10 — explicit legacy compatibility additions
Commit message: Add explicit legacy configuration compatibility previews.
Created: backend/app/config_data/compatibility_defaults_v1.json; backend/app/configuration/compatibility.py; backend/tests/test_configuration_compatibility.py; docs/refactor/LEGACY_COMPATIBILITY.md.
Modified: backend/app/configuration/service.py; backend/app/configuration/routes.py; backend/app/configuration/shadow_upgrade.py; backend/app/domain.py; backend/app/main.py; backend/tests/test_configuration_upgrade_api.py; docs/refactor/CHECKPOINT.md; docs/refactor/CHANGES.md; docs/refactor/VERIFICATION.md.
Changes: versioned seven-setting missing-only proposal, no overwrite of administrator values, no publication; admin preview routes with version preconditions; explicit --compatibility shadow option; strict boolean validation rejects integer lookalikes. Defaults captured from prior fallback behavior; review bypass remains disabled.
Verification: 13 compatibility tests passed; API/upgrade/initial compatibility selection 16 passed (overlapping runs). Read-only full-case rehearsal 54 eligible cases, 7049 ordered findings, 216 conversion occurrences, zero state/scoring differences and zero blockers; 18 cases used compatibility proposals; 13 had no supported conversions. Original payloads/case pins unchanged. No live migration or push.

## Step 11 — field-binding and applicability editor
Commit message: Add schema-driven comparison field and applicability controls.
Created: backend/app/configuration/field_options.py; backend/tests/test_comparison_field_options.py; frontend/components/comparison-fields.tsx.
Modified: backend/app/configuration/comparison.py; backend/app/configuration/generic_sop.py; backend/app/configuration/routes.py; backend/tests/test_configuration_store.py; backend/tests/test_configuration_upgrade_api.py; frontend/components/comparison-upgrade.tsx; docs/refactor/UPGRADE_PREVIEW.md; docs/refactor/SOP_CONFIGURATION.md; docs/refactor/CHECKPOINT.md; docs/refactor/CHANGES.md; docs/refactor/VERIFICATION.md.
Additional evidence outside Git: outputs/refactor-step11/field-applicability-editor.png. Generated next-env development import change restored.
Verification: final43 focused tests passed;5 API tests passed; TypeScript passed. Browser synthetic preview: converted rule, rebound source ektp.name, configured customer_type=INDIVIDUAL, edited label, Test settings accepted without publish. Zero preview documents means browser check validates configuration only. Visual evidence text discovered in choices and excluded plus backend rejection; self-comparison rejected. Preview servers stopped, live healthy.

## Step 12 — M1 atomic interactive publication
Commit message: Publish configuration revisions atomically across legacy and normalized storage.
Created: backend/app/configuration/publication.py; backend/app/configuration/verify_publication.py; backend/tests/test_configuration_publication.py; docs/refactor/PUBLICATION_SERVICE.md.
Modified: backend/app/main.py; backend/app/settings.py; backend/tests/test_configuration_migrations.py; docs/refactor/PLAN.md; docs/refactor/CHECKPOINT.md; docs/refactor/CHANGES.md; docs/refactor/MIGRATIONS.md; docs/refactor/VERIFICATION.md.
Change: publish endpoint delegates to application service; explicit legacy(default)/dual infrastructure rollout mode; requires migrated tables/checksums; Config, normalized publication and audit share transaction. Source request not mutated, historical case pins preserved. No startup table creation.
Verification: 17 API/publication/flow tests passed;5 PostgreSQL migration tests passed; final1 input-copy/prompt-compilation test passed. PostgreSQL rehearsal proposed41 and rolled back, round trip equal, original config/case/publication/audit rows unchanged. Live health ok; restored DB stopped. Other direct writers/normalized reads still pending; M1 partial, no activation or push.

## Step 13 — all configuration writers and explicit initialization
Commit message: Centralize configuration writers and remove startup policy upgrades.
Files:
- backend/app/configuration/initialize.py (created)
- backend/tests/test_configuration_writers.py (created)
- backend/app/configuration/publication.py
- backend/app/account_opening_official.py
- backend/app/account_opening_seed.py
- backend/app/domain.py
- backend/app/enum_aliases.py
- backend/app/extraction_quality.py
- backend/app/main.py
- backend/app/profile_guidance.py
- backend/app/profile_variants.py
- backend/app/spider_config.py
- backend/app/transaction_flows.py
- backend/app/worker.py
- backend/tests/conftest.py
- docs/refactor/PUBLICATION_SERVICE.md
- docs/refactor/PLAN.md
- docs/refactor/CHECKPOINT.md
- docs/refactor/CHANGES.md
- docs/refactor/VERIFICATION.md

Additional modified file: backend/tests/test_profile_guidance.py (compiled prompt-length fixture).
Verification: 4 new tests passed; broader run 26 passed/1 outdated fixture failed, fixture corrected but Docker rerun blocked. All backend Python parsed. This is implemented with final regression pending, not completed rollout. See CHECKPOINT for disk incident and preserved state.

## Step 14 — private object-backup tooling (execution blocked)
Commit message: Add guarded logical object backup and integrity verification.
Created: backend/app/configuration/backup_objects.py; backend/tests/test_object_backup.py.
Modified: docs/refactor/CHANGES.md; docs/refactor/CHECKPOINT.md; docs/refactor/VERIFICATION.md.
Behavior: credentials remain inside existing API container; read-only list/get requests; inventory-before/after guard, per-object SHA256 manifest and archive verification; exclusive output creation; free-space preflight; subprocess timeouts; remove only its own failed output. Never writes live objects or extracts untrusted archive paths. Backup captures current object contents only, not version histories or a transactionally coordinated database snapshot.
Tests: 3 offline integrity tests passed (valid content, corrupted digest, unexpected member). No completed production object backup: initial attempt exhausted C:, subsequent inventory blocked by Docker. B0/C1 remain incomplete.
Step13 commit: d03877a. No live activation/public push.

## Step15 — verified pinned configuration repository
Commit message: Route pinned configuration reads through a verified repository.
Created: backend/app/configuration/repository.py; backend/tests/test_configuration_repository.py.
Modified: backend/app/case_processing.py; backend/app/dataset_comparison.py; backend/app/domain.py; backend/app/field_reprocessing.py; backend/app/grouping_repair.py; backend/app/main.py; backend/app/processor.py; backend/app/settings.py; docs/refactor/PUBLICATION_SERVICE.md; docs/refactor/INVENTORY.csv; docs/refactor/PLAN.md; docs/refactor/MIGRATIONS.md; docs/refactor/VERIFICATION.md; docs/refactor/CHANGES.md; docs/refactor/CHECKPOINT.md.
Behavior: copied snapshots, pinned-ID resolution, legacy/verify/normalized infrastructure modes, dual-write precondition, fail closed on missing/linkage/digest/parity errors. No live flags changed. Guidance/upgrades use centralized writes. Existing case pins preserved.
Verification:22 focused plus52 broader tests passed.40 revisions/67 pins parity checked read-only. PostgreSQL publication rollback rehearsal passed. Object baseline backup verified. M1 complete in isolation; remaining plan points not marked complete. Tracking documents repaired to UTF-8 where prior mixed encodings existed.

## Step16 — database-enforced revision immutability
Commit message: Enforce immutable configuration revisions in PostgreSQL.
Created: backend/app/configuration/migrations/0004_revision_immutability.sql.
Modified: backend/app/configuration/migrate.py; backend/app/configuration/README.md; backend/tests/test_configuration_migrations.py; docs/refactor/CHANGES.md; docs/refactor/CHECKPOINT.md; docs/refactor/MIGRATIONS.md; docs/refactor/VERIFICATION.md; docs/refactor/PLAN.md.
Changes: mutation triggers for six normalized tables and legacy configurations; transaction-bound child inserts; parameter-free migration script execution. No live migration.
Verification:6 PostgreSQL tests passed, including21 table mutation attempts and5 late-insert attempts; new revision/idempotent import preserved. Migration0004 applied/replayed on isolated restore;40 revisions round-trip, original rows unchanged. New publication rehearsal proposed41/rolled back/equal, originals unchanged. Docker restart succeeded; live services healthy.

## Step17 — legacy refresh and grouping regressions
Commit message: Fix legacy case refresh and correct grouping regression coverage.
Created: backend/tests/test_legacy_case_refresh.py.
Modified: backend/app/domain.py; backend/tests/test_grouping.py; docs/refactor/CHANGES.md; docs/refactor/CHECKPOINT.md; docs/refactor/VERIFICATION.md; docs/refactor/INVENTORY.csv.
Removed misplaced profile-upgrade code from legacy refresh; case evaluation never changes published profile policy. Grouping fixture now expects3 distinct byte streams; separate identical-content test confirms1 document/job/case.17 tests passed; strengthened legacy idempotency assertions rerun2 passed. Removed clean, obsolete baseline-regression worktree after confirming no changes; baseline commit remains reproducible in Git. No live changes.

## Step18 — shared configurable case-context registry
Commit message: Configure case context definitions across rules and review forms.
Files:
- backend/app/config_data/context_defaults_v1.json (created)
- backend/app/configuration/contexts.py (created)
- backend/app/configuration/migrations/0005_context_definitions.sql (created)
- backend/tests/test_context_configuration.py (created)
- frontend/components/context-editor.tsx (created)
- frontend/components/context-inputs.tsx (created)
- backend/app/configuration/generic_sop.py
- backend/app/configuration/routes.py
- backend/app/configuration/store.py
- backend/app/domain.py
- backend/app/main.py
- backend/app/sop.py
- backend/tests/test_configuration_migrations.py
- backend/tests/test_generic_sop_runtime.py
- frontend/app/settings/page.tsx
- frontend/components/case-sop.tsx
- frontend/lib/types.ts
- backend/app/configuration/README.md
- docs/refactor/CHANGES.md
- docs/refactor/CHECKPOINT.md
- docs/refactor/VERIFICATION.md
- docs/refactor/MIGRATIONS.md
- docs/refactor/INVENTORY.csv
- docs/refactor/PLAN.md

Behavior: typed choice/text/digits/document-reference definitions, labels, limits and family/profile bindings; dedicated immutable publication rows; explicit-empty versus absent compatibility; versioned defaults captured from legacy behavior. Default bootstrap includes definitions, existing history unchanged. Rule conditions/options, API edits and case form read one registry. Case catalog resolves the pinned config, preventing later version options from leaking into existing cases. No automatic historical rewrite or live publication.
Verification:39 focused backend tests;43 automation/Forex/encoding regressions;6 PostgreSQL migration tests; final strengthened registry/migration/runtime selection24 passed. TypeScript passed. Isolated browser copied legacy definitions into local draft, added enum, edited choices, Test settings accepted; published version stayed7. Zero preview documents, so no extraction-result claim. Screenshot outside Git: outputs/refactor-step18/context-editor.png. Migration0005 rehearsed only on restored sqe_refactor;40 unchanged round trips, replay0; publication rollback exact.
Cleanup: preview API/database stopped, Next dev ended, browser tab closed, generated next-env change restored, scoped ignored frontend/.next removed using git clean after dry-run. No image build; --rm test runners. Old94 MB O: cache remains after policy rejection of its recursive deletion.

## Step19 — custom profile contracts and runtime adapter
Commit message: Support configured document profiles through extraction and review.
Files:
- backend/app/configuration/profiles.py (created)
- backend/tests/test_custom_profiles.py (created)
- frontend/components/profile-create.tsx (created)
- backend/app/domain.py
- backend/app/extraction_quality.py
- backend/app/main.py
- backend/app/processor.py
- backend/app/provider.py
- frontend/app/settings/page.tsx
- frontend/lib/types.ts
- backend/app/configuration/README.md
- docs/refactor/CHANGES.md
- docs/refactor/CHECKPOINT.md
- docs/refactor/VERIFICATION.md
- docs/refactor/INVENTORY.csv
- docs/refactor/PLAN.md

Behavior: custom profile IDs/schemas/labels/classification descriptions/suffixes/family membership can be published; explicit schema adapter validates structural shapes and missing required data. Native adapters cannot be replaced. Unenforced constraints/policy keys and nonfinite values rejected. Schema lookup uses saved definitions throughout configuration reads, extraction, review corrections and field reprocessing. UI creation adds an editable starter profile to the selected family draft. Fixture mode rejects new profiles without fixture files. Native compatibility catalog remains required; arbitrary removal of built-in profiles is not implemented.
Verification:20 custom/guidance/reprocessing tests passed;5 final contract tests;10 schema/reusable-profile/variant regressions; extended custom upload/extract/SOP/report/selected-field-reprocess test passed24.18s. External provider mocked; no paid extraction. TypeScript passed. Browser created supporting_note, selected it, Test settings accepted0-document draft, published version7 unchanged. Screenshot outside Git: outputs/refactor-step19/custom-profile.png.
Cleanup: preview servers/tab stopped, generated next-env restored, scoped ignored .next removed after dry-run. No image build or extra backup. Live API remained healthy. Remaining generic rule creation UI follows next.

## Step20 — create new comparison rules in configuration UI
Commit message: Add new text comparisons directly to configuration drafts.
Modified: frontend/components/comparison-upgrade.tsx; docs/refactor/CHANGES.md; docs/refactor/CHECKPOINT.md; docs/refactor/VERIFICATION.md; docs/refactor/PLAN.md.
Changes: create comparisons from registered schema text fields, unique IDs, explicit schema bindings, distinct-field guard, case/whitespace matching, rule-order and explicit family-scope updates. Field options load even before a generic rule exists, refresh when context definitions change and debounce requests. Dropdown paths distinguish nested fields with the same label.
Verification: TypeScript passed. Browser created synthetic_name_match from ektp.name to riplay.customer_name, validated draft, selected new rule in flow, validated again. Publishedv7 unchanged;0 preview documents. Screenshot outside Git: outputs/refactor-step20/new-comparison.png. No backend changes or cloud calls. Preview stopped, tab closed, next-env restored and scoped .next removed after dry-run.

## Step21 — provider-neutral extraction application boundary
Commit message: Introduce typed extraction service and explicit provider adapters.
Files:
- backend/app/extraction/__init__.py (created)
- backend/app/extraction/contracts.py (created)
- backend/app/extraction/adapters.py (created)
- backend/app/extraction/service.py (created)
- backend/app/configuration/codec.py (created)
- backend/tests/test_extraction_service.py (created)
- backend/app/provider.py
- backend/app/configuration/store.py
- backend/app/configuration/compatibility.py
- backend/app/configuration/upgrade_comparisons.py
- docs/refactor/CHANGES.md
- docs/refactor/CHECKPOINT.md
- docs/refactor/VERIFICATION.md
- docs/refactor/INVENTORY.csv
- docs/refactor/PLAN.md

Behavior: typed request/result and adapter protocol, explicit code-owned registry, deep-copied pinned configuration with canonical fingerprint, fail-closed unsupported providers/malformed results. Legacy run_provider facade delegates through application service. Existing Llama pipeline and fixture implementation retain checkpoints, classification and reuse behavior. Service adds no retries or hidden paid calls. ProcessingIssue remains import-compatible. Canonical hashing moved to framework-independent codec with old store import preserved.
Verification:47 service/provider/field-recovery/config-store tests passed204.05s;3 focused Llama classification/parse-reuse/uncertainty tests passed33.77s. All providers mocked/fixture, no paid model requests. No live change, new images or large artifacts. State/connector persistence and remaining provider internals still need separation.

## Step22 — explicit durable provider-state repository
Commit message: Serialize durable provider checkpoints through a state repository.
Files:
- backend/app/extraction/state_repository.py (created)
- backend/tests/test_provider_state_repository.py (created)
- backend/app/extraction/contracts.py
- backend/app/provider.py
- backend/app/domain.py
- backend/tests/test_custom_profiles.py
- frontend/components/profile-create.tsx
- docs/refactor/CHANGES.md
- docs/refactor/CHECKPOINT.md
- docs/refactor/VERIFICATION.md
- docs/refactor/INVENTORY.csv
- docs/refactor/PLAN.md

Changes: ProviderStateStore protocol and SQL implementation; checkpoint transactions explicitly commit before external effects; FOR UPDATE serializes state merges; nested state copied; missing-document and invalid-serialization paths fail without losing prior receipts. Legacy helper APIs delegate to repository. Custom profile ID limit aligned to Document.doc_type VARCHAR(50), including UI guard.
Verification:10 repository/custom-profile tests passed23.70s including real PostgreSQL blocked-writer merge;8 recovery/native reuse tests passed82.67s; TypeScript passed. Temporary PostgreSQL schema removed; no public data modified. --rm runners; isolated database stopped. No model calls/images/large artifacts. Atomic submission claiming across concurrent jobs remains a distinct responsibility; this change guarantees merge integrity, not a full lifecycle rewrite.

## Step23 — typed provider connectors and configurable request controls
Commit message: Preserve connector settings and share validated provider options.
Files:
- backend/app/config_data/provider_defaults_v1.json
- backend/app/extraction/connector_contracts.py
- backend/app/extraction/connector_repository.py
- backend/app/field_reprocessing.py
- backend/app/main.py
- backend/app/provider.py
- backend/app/spider_provider.py
- backend/tests/test_connector_contracts.py
- frontend/components/connector-options.tsx
- frontend/components/spider-connector.tsx
- frontend/app/settings/page.tsx
- docs/refactor/CHANGES.md
- docs/refactor/CHECKPOINT.md
- docs/refactor/VERIFICATION.md
- docs/refactor/PLAN.md

Changes: shared organization-scoped connector repository; encrypted credentials excluded from responses/repr; typed URL/key/numeric contracts; versioned compatible defaults; key-only updates merge submitted options instead of resetting model/scope; unknown legacy storage options preserved but not exposed or executed. Invalid saved options fail closed for extraction and show a repair warning in settings. Normal/selected-field providers use the same options, including timeouts and image budgets. Advanced UI controls derive limits from backend metadata.
Verification:48 connector/Spider/prompt-delivery/field-reprocessing tests passed373.81s; TypeScript passed; both restored connector rows validated without reading credentials. No real model calls or live changes. Browser validation of new advanced controls remains part of final UI acceptance.

## Step24 — immutable dataset registry and explicit reference resolution
Commit message: Register immutable reference datasets and reject unknown bindings.
Files:
- backend/app/configuration/datasets.py
- backend/app/configuration/dataset_sources.py
- backend/app/configuration/dataset_routes.py
- backend/app/configuration/import_datasets.py
- backend/app/configuration/migrations/0006_reference_datasets.sql
- backend/app/configuration/publication.py
- backend/app/dataset_comparison.py
- backend/app/document_families.py
- backend/app/main.py
- backend/app/settings.py
- backend/app/transaction_flows.py
- backend/tests/test_configuration_migrations.py
- backend/tests/test_dataset_registry.py
- frontend/components/dataset-select.tsx
- frontend/components/document-families.tsx
- frontend/components/transaction-flows.tsx
- docs/refactor/CHANGES.md
- docs/refactor/CHECKPOINT.md
- docs/refactor/VERIFICATION.md
- docs/refactor/MIGRATIONS.md
- docs/refactor/INVENTORY.csv
- docs/refactor/PLAN.md

Changes: typed private reference import, organization-scoped immutable dataset IDs/content hashes, migration0006 and PostgreSQL mutation guards; explicit baseline importer with expected-database check; bundled/verify/registry rollout; lazy compatibility sources rather than module-load private workbook data. Unknown dataset IDs fail without Forex fallback. Interactive publication resolves dataset bindings. Admin registry imports audited by ID/digest; catalog omits values. Family/flow dataset selectors use server catalog.
Verification:22 dataset/API/migration tests passed17.73s; TypeScript passed.40 configuration histories unchanged after migration; baseline2 datasets imported to isolated DB.67 case comparison results exactly equal between bundled and registry modes in read-only rehearsal. Browser selector shows real catalog; Step23 advanced control saved/reloaded/restored in synthetic preview, publishedv7 unchanged. Screenshot outputs/refactor-step24/connector-controls.png. Preview stopped and cache cleaned. No live writes or external model calls. Registry activation/report read models/comparison policy configuration remain pending.

## Step25 — typed report read projections and mapping editor
Commit message: Configure report data sources through versioned bindings.
Files:
- backend/app/config_data/report_bindings_v1.json
- backend/app/configuration/reporting.py
- backend/app/configuration/report_routes.py
- backend/app/configuration/store.py
- backend/app/domain.py
- backend/app/main.py
- backend/app/kertas_kerja.py
- backend/app/account_opening_report.py
- backend/tests/test_report_bindings.py
- frontend/components/report-bindings.tsx
- frontend/components/document-families.tsx
- frontend/lib/types.ts
- docs/refactor/CHANGES.md
- docs/refactor/CHECKPOINT.md
- docs/refactor/VERIFICATION.md
- docs/refactor/PLAN.md
- docs/refactor/INVENTORY.csv

Changes: versioned compatible report binding defaults; typed source/document/context/customer/literal mappings and timezone; schema/context existence validation; explicit customer fallback; immutable configuration entries for report_definitions. Forex/account-opening renderers consume pure projections, retaining layout/scoring. Family report settings exposes draft editor and validates before publication.
Verification:14 initial report checks; extended run31 passed/1 fixture failure (Python tuple vs stored JSON array), fixture canonicalized; final25 report/storage checks passed8.96s. TypeScript passed.449 saved report rows identical to previous implementation in read-only comparison. Browser edited UTC draft, Test settings succeeded0 documents; discarded draft, publishedv7 unchanged. Screenshot outputs/refactor-step25/report-mappings.png. Preview stopped/cache cleaned; temporary baseline helper removed. No live/model calls. Other report presentation/category defaults and full acceptance remain pending.

## Step26 — explicit provider-independent field validation
Commit message: Apply configurable data checks without weakening native validation.
Files:
- backend/app/configuration/field_checks.py
- backend/app/domain.py
- backend/app/provider.py
- backend/app/spider_result.py
- backend/app/config_workbook.py
- backend/app/main.py
- backend/tests/test_field_checks.py
- frontend/components/field-checks.tsx
- frontend/app/settings/page.tsx
- frontend/lib/types.ts
- docs/refactor/CHANGES.md
- docs/refactor/CHECKPOINT.md
- docs/refactor/VERIFICATION.md
- docs/refactor/PLAN.md
- docs/refactor/INVENTORY.csv

Changes: typed text/identifier/date/number/choice/boolean field policies in immutable profiles; exact digit counts, explicit numeric separators/currency, required/optional and incomplete-observation handling. Visual-region fields excluded. Spider configured fields receive real check outcomes while unchecked fields/native normalization remain SKIPPED. Native/custom providers use same additional checks and cannot weaken pre-existing failure/uncertainty. Values remain unchanged. Profile UI configures draft checks; configuration workbook imports/exports field checks and report definitions, preserves old templates, rejects oversized Excel cells instead of truncating; API returns clear422.
Verification:32 initial field/Spider checks passed141.33s;39 native/custom/reread checks passed156.95s;69 field/workbook/Forex/account tests passed100.26s; final25 field tests passed3.53s including direct SOP points1/0. TypeScript passed. Browser NIK16-digit draft Test settings succeeded0 documents; discarded/publishedv7 unchanged. Screenshot outputs/refactor-step26/field-validation.png. Preview/cache cleaned, no model/live calls. Existing pinned profiles have not been silently assigned new checks: explicit policy proposal/import and acceptance still required before cutover.

## Step27 — typed account SOP policies and explicit applicability
Commit message: Validate account policy contracts and configure requirement triggers.
Files:
- backend/app/configuration/account_policies.py
- backend/app/configuration/account_policy_routes.py
- backend/app/configuration/shadow_conditions.py
- backend/app/config_data/account_conditions_v1.json
- backend/app/account_opening_sop.py
- backend/app/sop.py
- backend/app/main.py
- backend/tests/test_account_policy_contracts.py
- frontend/components/account-condition.tsx
- frontend/components/automation-editor.tsx
- docs/refactor/CHANGES.md
- docs/refactor/CHECKPOINT.md
- docs/refactor/VERIFICATION.md
- docs/refactor/PLAN.md
- docs/refactor/INVENTORY.csv

Changes: strict policy grammar rejects unknown/unused settings and unbounded format regex; captured account policies retain identical JSON. Explicit source/true-values/false-values conditional predicates require unique completed verified source; unknown data never excludes a requirement. Existing legacy conditional branch retained for historical profiles. Three established criteria captured separately as bootstrap proposal data; undefined survey/signature criteria not invented. Draft editor provides explicit requirement configuration; pure proposal and read-only streaming rehearsal do not publish.
Verification:30 focused account tests passed66.29s;45 official/SOP/point/generic tests passed41.94s; TypeScript passed;6180 policies across40 histories validate unchanged. First conditional rehearsal36 cases/5623 findings/108 conversions0 score/outcome differences,18 histories require compatibility defaults; compatibility rehearsal still running.503-test full backend suite started against frozen runtime; no final result yet. New conditional editor awaits final browser acceptance.
