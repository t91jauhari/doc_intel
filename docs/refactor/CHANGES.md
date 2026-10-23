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

## Step28 — public-source export guard and final regression progress
Commit message: Guard clean source exports and verify dynamic dataset publication.
Files:
- scripts/export_public_source.py (created)
- scripts/test_export_public_source.py (created)
- backend/tests/test_document_families.py
- backend/tests/test_dataset_registry.py
- docs/refactor/CHANGES.md
- docs/refactor/CHECKPOINT.md
- docs/refactor/VERIFICATION.md

Changes: audit-first allowlist export, no Git history/private fixtures/workbook values/screenshots; generated empty synthetic references; hashes/size manifest; new output directory only; bounded credential/identifier-shape blockers without echoing values; batched Git blob reads. Dynamic dataset test now rejects malformed IDs rather than all new IDs; publication tests enforce registered-only binding and unchanged revision after rejection.
Verification:4 exporter unit tests passed; first audit284 files/2.22MB/192 excluded/no blockers, no output written.20 family/dataset API tests passed51.32s. Full backend first segment177 passed/7 PG skips then outdated fixed-family assertion failed; corrected fixture and reran affected tests. Remaining files from test_document_families onward running in session98361; do not claim full suite green yet. Conditional rehearsal with compatibility:54 cases/7049 findings/162 conversions/18 compatibility cases/0 mismatches/0 blocked; read-only. No public push or live activation.

## Step29 — honor explicitly requested Spider enum revalidation
Commit message: Apply audited enum aliases during Spider revalidation.
Files:
- backend/app/enum_aliases.py
- backend/app/spider_result.py
- backend/app/main.py
- backend/tests/test_enum_display.py
- backend/tests/test_spider_enum_revalidation.py (created)
- docs/refactor/CHANGES.md
- docs/refactor/CHECKPOINT.md
- docs/refactor/VERIFICATION.md

Changes: explicit enum-revalidation receipts now apply approved canonical/alias spelling and raw fallback to Spider reports, preserve original raw/other fields, record transformations/source configuration and keep uncertainty. Unrequested extraction unchanged; configured field checks still run afterward. Reject requests without applicable profile fields. Native-only tests choose native provider explicitly instead of assuming default Spider normalizes.
Verification:40 enum/Spider/field tests passed12.37s; broader remaining suite from test_enum_display running session7895, currently past45percent; do not claim final green. Separate PostgreSQL migration7 tests passed1.24s. Exported previous-head synthetic suite76 passed35.15s. Frontend production build compiled/TypeScript/static pages successfully. Automatic approval review rejected production preview start with only blocked-by-policy/no detailed reason; new conditional editor browser acceptance remains pending. Preview stopped/cache removed after dry-run. No live/model calls.

## Step30 — family isolation and readonly source startup
Commit message: Scope report mappings to families and defer filesystem writes.
Files:
- backend/app/configuration/reporting.py
- backend/app/configuration/initialize.py
- backend/app/settings.py
- backend/tests/test_report_bindings.py
- backend/tests/test_infrastructure_settings.py
- backend/tests/test_parse_evidence.py
- frontend/components/report-bindings.tsx
- frontend/components/document-families.tsx
- frontend/lib/types.ts
- docs/refactor/CHANGES.md
- docs/refactor/CHECKPOINT.md
- docs/refactor/VERIFICATION.md

Changes: per-family report_definition overrides stored in immutable family revisions; other families sharing the renderer retain their mappings. Document/context bindings constrained to family scope; global legacy definitions retained as fallback. Family editor now writes its family override. Settings import no longer creates directories; explicit development initialization creates SQLite parent, storage writes already create their own parents. Native retry regression explicitly selects mocked Llama provider.
Verification:26 family/report/latest tests passed67.22s; TypeScript passed;19 settings/report/writer/enum tests passed60.34s including source-import write prohibition and SQLite initialization in new nested directory. Retry checkpoint test passed14.10s. Previous broad remainder163 passed before incorrect native-provider fixture; fixed fixture. Remaining tail to resume from test_parse_evidence. Generated standalone trace dependency folder136KB verified inside checkout/no links, dry-run/scoped git clean removed. No live changes or external jobs.

## Step31 — import private references outside the public tree
Commit message: Support bounded organization-specific reference file imports.
Files:
- backend/app/configuration/import_datasets.py
- backend/tests/test_dataset_registry.py
- scripts/export_public_source.py
- docs/refactor/CHANGES.md
- docs/refactor/CHECKPOINT.md
- docs/refactor/VERIFICATION.md

Changes: optional external --reference-file imports require --organization and explicit expected database; bounded50MBJSON parse/typed validation without logging source values; transactional immutable registration remains authoritative. Public export includes new synthetic enum/settings/dataset tests and documents private import/new immutable IDs.
Verification:11 dataset registry/API/import tests passed30.62s. Public candidate1 remains previous-head and not for release. Remaining tail session39864 running from test_parse_evidence; no runtime mutation of imported tail modules. No private data in Git or public push.


## Step 32 — Remove Llama application provider
User requested removal of Llama, superseding the Step 31 custom-profile Llama support gap. Removed its adapter, paid execution implementation, connector settings form, and unused parser tier/version controls. New configuration publication accepts Spider-AI or development fixtures only. Historical Llama configurations remain readable; extraction and selected-field reprocessing fail explicitly before submission and require an explicit case upgrade. Legacy connector routes return HTTP 410, without deleting stored credentials or historical receipts. Native deterministic validation remains available. Standalone engine compatibility and historical SDK error decoding are not application provider integrations.

Files: backend/app/{domain,main,provider,field_reprocessing}.py; backend/app/extraction/{adapters,service,connector_repository}.py; frontend/app/settings/page.tsx; frontend/components/spider-connector.tsx; backend/tests/test_extraction_service.py; docs/refactor/{CHECKPOINT,CHANGES,VERIFICATION}.md.

Verification: 14 focused extraction/removal tests passed; frontend TypeScript check passed; git diff --check passed. Original live stack unchanged; this change is implemented in the isolated refactor only, not deployed. Earlier broad backend tail run was stopped on this owned test runner when scope changed; old Llama integration tests require retirement/replacement before a full-suite acceptance claim. Broader refactor phases remain pending. No provider calls, data migrations, paid jobs, or public pushes performed.


## Step 33 — Provider removal regression cleanup
Removed obsolete Llama paid integration tests; retained the standalone engine and historical error decoding tests. Native deterministic validator unit cases now explicitly select development fixtures; custom-profile tests select Spider. Connector encryption/access tests exercise Spider. Upload/dashboard labels now describe the supported provider accurately; historical case labels remain visible. Corrected a non-UTF-8 settings label and made public export reject invalid source encoding with a clear diagnostic.
Files: backend/tests/{test_connector_contracts,test_custom_profiles,test_enum_display,test_field_reprocessing,test_parse_evidence,test_platform,test_prompt_delivery,test_schema_descriptions}.py; frontend/app/{page,settings/page,upload/page,cases/[id]/page}.tsx; scripts/{export_public_source,test_export_public_source}.py; docs/refactor/{CHECKPOINT,CHANGES,VERIFICATION}.md.
Verification: initial full run 130 passed/7 PG skipped before obsolete connector expectation; 5 exporter tests and frontend type check passed. Three isolated backend shards are running (sessions64280,44135,41827); shard2 restarted at custom profiles after provider selection correction (42 earlier passes). Runtime source frozen until they finish. New comparison policy module/manifest/editor are unintegrated work in progress, not active or accepted. No live changes.


## Step 34 — Configurable reference comparison and application services
Family comparison_policy now controls conservative text comparison enablement, review/acceptance similarity, length/edit limits, and field/suffix exclusions. Release defaults captured in config_data/dataset_comparison_v1.json. Typed validation rejects unused/invalid options; changed numeric tokens still prevent fuzzy matches. API comparison resolves the case-pinned family policy and includes policy in the comparison fingerprint/result. Family configuration has an editor using server defaults. No extraction values or SOP scores are rewritten.
Configuration replay moved from API into configuration/replay.py with caller-owned read session. Latest report selection moved into ReportQueries/ReportAudience, preserving access filtering before ranking and eliminating one case lookup per report.
Files: backend/app/{dataset_comparison,domain,main,report_queries}.py; backend/app/configuration/{dataset_policy,replay}.py; backend/app/config_data/dataset_comparison_v1.json; backend/tests/{test_dataset_policy,test_platform,test_storage}.py; frontend/components/{dataset-policy,document-families}.tsx; frontend/lib/types.ts; docs/refactor/{CHECKPOINT,CHANGES,VERIFICATION}.md.
Verification: sharded baseline covered all507 backend tests after retiring removed Llama tests; PostgreSQL-only cases separately passed (11 checks, including8 previously skipped), Temporal2 passed on ephemeral test service. Shards173passed/7skipped;190passed before stale storage expectation plus corrected21tail (4 repeated);42 before custom provider correction plus75resumed/1skipped plus2Temporal. Fixed storage expected-byte assertion using shared uploaded_pdf helper; no storage implementation defect. New comparison/report/replay affected selections27+5 passed; TypeScript passed. Read-only old-vs-new comparison on67restoredcases/3028fields:0differences,0writes. All11 new policy checks passed, including publication and pinned-case isolation. Current backend collection518tests; baseline507 covered plus11 new checks. UI browser acceptance still outstanding after earlier automatic preview launch rejection. R1/R2/D1/D2/C1 broader remaining work is not complete. No live activation.


## Step35 — Configuration boundary and production release preparation
ConfigurationEnvelope validates root shapes and finite JSON before profile/policy processing, retaining unknown extensions without adding defaults to the stored payload. Configuration read/publication/replay/catalog/workbook HTTP endpoints moved from main.py to configuration/api.py; application publication/replay services and request/response contracts are retained. Root provider ID validation remains application-owned; historical configurations remain readable.
Files: backend/app/configuration/{contracts,api}.py; backend/app/{domain,main}.py; backend/tests/test_configuration_contracts.py; backend/tests/test_dataset_policy.py (synthetic standalone upload helper); docs/refactor/{CHECKPOINT,CHANGES,VERIFICATION,PLAN,INVENTORY.csv}.
Verification:30 root/custom-profile/writer/comparison checks passed;40 historical revisions passed structural validation with0 payload changes. Current interface production build passed using documented --webpack mode; default Turbopack rejected the intentionally shared dependency junction. TypeScript/static page generation passed. No preview server started. Generated .next and isolated tracing artifacts removed after resolving paths inside this checkout. All16 configuration-router regressions passed; no claim of final browser acceptance.
Release preparation: compose.production.yaml requires externally supplied image references/DB/object storage/Temporal/secrets, secure cookies/TLS, separate deployment name/queue, readonly runtimes and loopback frontend binding. docs/refactor/ROLLOUT.md records coordinated capture, import/verification gates, rollout and receipt-aware rollback. Compose schema validation and5 export-guard tests passed. These are prepared files, not an activated release. Public exporter includes only the deployment runbook among refactor records. All live code/data remain unchanged.


## Step36 — Captured native catalog instead of Python business literals
Moved native profile labels/classification descriptions/filename aliases, grouping prefixes/messages, family defaults, Forex vocabulary/checkpoint labels and historical rule patches into config_data/native_catalog_v1.json. Existing publications still supply their saved profile/grouping/policy settings; this release data is for seeding and explicit historical compatibility, never an automatic publication. The two historical policy_review conversions now use declarative when/set data rather than rule-ID branches in Python. Concrete configured operators remain unchanged.
Files: backend/app/{domain,document_families,forex_sop}.py; backend/app/configuration/native_catalog.py; backend/app/config_data/native_catalog_v1.json; docs/refactor/{CHECKPOINT,CHANGES,VERIFICATION}.md.
Verification: exact default_config fingerprint parity; family catalog equality;43 legacy rule projections equal before/after,0 differences and0writes. Forex27 tests passed. All28 grouping/Windows-encoding/family checks passed. This externalizes seed/compatibility data; it does not remove the native engine adapter requirement or finish all remaining service boundaries. No live changes or provider calls.


## Step37 — Provider settings application boundary
Connector administration now uses extraction/administration.py inside caller-owned transactions. extraction/api.py owns authenticated settings routes and removed-provider410 routes. Main composes routers instead of managing credentials. Known advanced settings, legacy private options, encryption and audit behavior remain preserved. Removed unused Llama options DTOs and prompt builders; standalone engine and historical SDK error decoding remain available without registering Llama extraction.
Files: backend/app/extraction/{administration,api,connector_contracts,connector_repository}.py; backend/app/{main,extraction_prompts}.py; docs/refactor/{CHECKPOINT,CHANGES,VERIFICATION}.md.
Verification: All31 connector/service/prompt checks passed. No provider calls or live writes. Public remote inspected read-only and has no refs; refresh sanitized source before considering any public publication. Never push this private history.


## Step38 — Public snapshot privacy and standalone engine acceptance
Sanitized customer-specific sample filenames/comments/docs and upload examples with generic customer placeholders. Native default policy stamp references now instruct administrators to configure an authorized reference; existing DB revisions/pins are untouched. Export guard now rejects private Google document links as well as invalid UTF-8/credential shapes, rather than publishing document identifiers. Generated public README states the refactor is still in progress.
Files: backend/app/domain.py (comment only); frontend/app/upload/page.tsx (example labels); engine/profiles.py (legacy CLI example paths); engine/{README,ektp/README,invoice/README,lld/README,riplay/README,valas1/README,valas2/README}.md; engine/{ektp,riplay}/policy.json (reference metadata only); engine/tests/test_ektp.py; scripts/{export_public_source,test_export_public_source}.py; docs/refactor/{CHECKPOINT,CHANGES,VERIFICATION}.md.
Verification: clean source candidate from Step37 has304files/2.25MB/0 scanner blockers and126 included synthetic tests passed without customer fixtures. Subsequent privacy changes require fresh export. All199 engine tests plus81 subtests passed. Engine test failure was an outdated expectation: approved enum aliases pass; missing enum values FAIL; unsupported enum text requires review and configured raw fallback is retained. Only tests were aligned; validator behavior did not change. Six export-guard tests passed. No public push yet; never push the private history.


## Step39 — Clean GitHub snapshot awaiting authentication
Fresh public export: work/refactor/public-source-candidate-step38, source54e0af3,304files/2.25MB,305staged including manifest,0 private reference rows.126 synthetic tests passed on the fresh export; every file hash/size verified. Created independent main commit9a685d4 (human Git identity/message), with no original history. git push --set-upstream origin main is waiting in Git Credential Manager (exec61612, credential-manager PID18372); no remote success/refs confirmed. User authentication requested asynchronously. Do not push from the private source checkout, force-push, or claim publication completed. Future accepted source changes need a new sanitized export/update to this clean history.

## Step40 — Explicit family catalogs and workbook prompt repair
family_catalog_mode=explicit allows a catalog containing only configured families/profiles. Absent mode retains exact legacy starter behavior. Removed mandatory native profile guard only for explicit mode; field/schema/context/rule bindings remain validated. UI family list and selection honor explicit mode; the settings switch materializes the current list safely. Workbook round trips preserve optional mode. Custom-only upload/extraction/SOP/report/selected-field retry works with no native profiles.
Found/fixed real workbook defect: profiles using the default system instruction exported an empty cell that failed reimport. Export now writes the effective instruction actually used by extraction. Both legacy and custom-only round trips prove instruction parity; no published configuration is changed by export.
Files: backend/app/{domain,document_families,config_workbook}.py; backend/app/configuration/contracts.py; backend/tests/test_custom_profiles.py; frontend/{lib/types,lib/document-family,components/document-families,app/settings/page}.tsx/ts; frontend/tests/document-family.cjs; work/refactor/start-preview.ps1 (local operation helper, outside repository); docs/refactor/{CHECKPOINT,CHANGES,VERIFICATION,PLAN}.
Verification:30 custom-profile/family/automation checks passed, including full custom-only pipeline and selected-field guidance persistence; TypeScript and frontend family assertions passed. No paid calls or live changes. Synthetic isolated API restarted and healthy on8100; web3100 remains unstarted after earlier automatic approval rejection. User asked asynchronously to run the supplied preview launcher. Preview v7/zero-document baseline must remain unpublished during browser checks. Remaining complex/visual policies, API boundaries and final activation are still not complete.

## Publication and preview recovery — 2026-10-23
The connected GitHub account confirmed repository ownership/write access. Published the previously verified sanitized Step38 snapshot (304 source files plus manifest) through GitHub tree/commit APIs. Remote main verified independently with git ls-remote: d22e168eaf9e7bbc66e5c6447c4dfb58886014a9. No private history or customer artifacts published. Earlier credential-manager push was stopped after verifying its owned process chain; no authentication workaround or credential export was used.
Isolated web preview is running on 127.0.0.1:3100 (webpack development mode), connected to synthetic API8100, published v7 and zero documents. Renewed user authorization permitted automatic launch; no manual startup remains required. Browser verified family catalog switch, comparison settings controls and read-only draft test with zero document replay. Draft must be discarded after remaining acceptance checks. Step41 API split remains uncommitted and full backend regression is running (exec3771); do not publish this unverified split yet.
Files changed this step: backend/tests/test_configuration_publication.py (patch moved configuration router settings rather than old main module); docs/refactor/{CHECKPOINT,CHANGES,VERIFICATION,PLAN}.md. API module inventory will be recorded after regression acceptance.

## Step41 — API feature boundaries (verification in progress)
Moved the remaining 55 route handlers and 19 request models out of the application entry point. main.py now contains lifecycle, middleware, health and router composition. Endpoint bodies, transaction boundaries and authorization checks are preserved. OpenAPI parity verified all65paths and their methods/parameters/status/request/response contracts; only tags and one internal PreviewInput schema namespace changed. Some feature routers still perform direct database orchestration; service separation remains explicitly tracked rather than claimed complete.
Created: backend/app/api/{__init__,dependencies,contracts,views,authentication,administration,intake,documents,operations,cases,comparisons,evidence,field_processing,notifications,reports,exports}.py and backend/app/api/README.md.
Changed: backend/app/main.py; backend/tests/test_configuration_publication.py; docs/refactor/{CHECKPOINT,CHANGES,VERIFICATION,PLAN,INVENTORY.csv}.
Browser acceptance: explicit family catalog switch; family comparison editor and read-only test; conditional EDD source/values editor; Spider/development-only provider choices; draft discarded; restart against extracted API routers successful. Synthetic state verified directly: published7,0documents. TypeScript check passed. Full backend suite exec3771 and Temporal exec34714 still running; no Step41 commit/public export until accepted.
Public repository main remains verified Step38 snapshot d22e168. API8100 and web3100 run isolated code; original8000/3000 remain unchanged.
Step41 additional files: backend/tests/test_spider_provider.py now verifies effective workbook prompt parity and exactly one spatial-grounding section; raw custom instructions and old-template behavior remain covered. docs/refactor/CONFIGURATION_SCHEMA.md now distinguishes implemented tables from the original proposed entity list. The sole regression failure was a stale raw-prompt expectation after Step40's effective-prompt export repair; no extraction behavior changed to satisfy it.

## Step41 accepted — 2026-10-23
All528 backend tests covered successfully: initial276passed/7PGskipped; remaining shards81passed,71passed before stale workbook expectation, corrected tail10passed,80passed/1PGskipped; Temporal2passed; PostgreSQL11passed covers all8skips (3 additional checks repeat previously passing tests). Unique total:518non-Temporal withoutPG +2Temporal +8PG =528. No outstanding test failures. PostgreSQL tests use dedicated disposable schemas on the isolated restore. Only a Starlette test-client deprecation warning remains. Engine unchanged since its199tests+81subtests acceptance. TypeScript passed; browser acceptance and65path OpenAPI parity passed.
Step41 is implemented and tested in isolation. Remaining command-service separation, complex/visual policies, native field-policy acceptance and coordinated cutover are still tracked as incomplete. This is not a live activation or a complete architecture claim. Generated frontend/next-env.d.ts changes belong to the active development preview and are excluded from the commit.
Next: fresh sanitized export from the accepted commit, verify manifest/source guards and included synthetic tests, then update public main with an expected-head lease. Never push private Git history.

## Step41 publication complete — 2026-10-23
Accepted private implementation commit:a469dd8. Fresh sanitized candidate:work/refactor/public-source-candidate-step41,321sourcefiles/2,263,135bytes plus manifest. Source guards:0blockers; all321hashes/sizes verified;6export-guard tests passed;126included synthetic tests passed111.10s. Public main independently verified11520ede47b0025d10232d3eead01819e7d887ee (parentd22e168) through git ls-remote after an expected-head, non-force connector update. No private history, credentials or customer artifacts published.
All test containers removed themselves. Original API8000 and isolated API8100 healthy. Web3100 remains running (exec89237) with active development cache; browser tab10 shows configuration. Published synthetic state7/0 preserved. Only generated frontend/next-env.d.ts remains outside commits while preview is active.
Cleanup attempt for obsolete public-source-candidate, public-source-candidate-step37 and public-source-candidate-step38 was rejected by automatic approval review: blocked by policy. Those small copies remain; no alternate deletion or bypass attempted. Backups and the previously blocked preview cache remain retained. Do not retry rejected cleanup without new authorization.
Remaining refactor work: command-service separation beyond feature routers; complex/visual SOP contract generalization; remaining configuration entity/field-policy acceptance; final target-specific coordinated cutover and rollback. Current unit is complete, whole refactor is not declared complete. Resume from PLAN.md with the current source/publication facts rather than earlier authentication or manual-preview blockers.

## Step42 in progress — application services, remaining policies and entity tables
User confirmed final target: complete and verify locally first. Original app remains untouched.
Implemented (uncommitted):43 application operations extracted into backend/app/application; HTTP handlers delegate with unchanged contracts. Added transport-independent ApplicationError/access authorization; moved shared DTOs/projections to app/contracts.py and app/projections.py with API compatibility imports. Upload uses an UploadedFile protocol and AnyIO thread port. Feature-router unused imports pruned. End-to-end custom/platform27tests passed422.94s.
Added seven publication-scoped entity tables via0007_configuration_entities.sql; new publications use storage_version2, old immutable v1 publications still compile. Profile/flow/family/rule/report definitions no longer share generic entries for new revisions. Store/repository/publication30tests passed121.36s; PG migration/provider state11passed2.36s. Actual isolated restore migration/replay exec60740 running; no live migration.
Added configurable visual/date/money SOP policies, family score groups and editable signature-evidence bindings. Wired generic dispatch/scoring/review safeguards and UI policy editors. New policy/generic/rule42tests passed6.97s; TypeScript passed, latest editor changes need repeat check. Need browser review and full regression after code settles.
Captured18 prior constants from13 modules in config_data/extraction_seed_catalog_v1.json; tagged decoder preserves tuple/set types and returns copied defaults. Added score-group/evidence defaults to the same catalog. Existing publications remain authoritative; no startup upgrade/publication.
Created local one-time helpers outside Git: work/refactor/extract-application-step42.py and externalize-seeds-step42.py. Do not rerun extraction scripts against transformed code. API baseline saved private/api-step42-before.json.
Pending: source formatting/architecture guards; visual-review integration acceptance; v1/v2 history and saved-case parity; full sharded backend/engine/frontend/build verification; local release rehearsal; sanitized publication; final inventory/plan reconciliation. Current source not committed or published. Preview API must restart before browser checking latest code; published synthetic7/0 baseline remains intact. Old cleanup blocks still apply; do not retry those folders.


## Step42 accepted locally — 2026-10-23
554 unique backend tests covered: shard0 143passed/1PGskip; shard2
216passed/7PGskips; shard1 102passed before runner correction plus83passed
in corrected tail. The8 PostgreSQL-dependent skips passed in PG integration
(11passed including3 overlap checks); Temporal2passed. Unique coverage:
544 non-Temporal/non-PG +8PG +2Temporal =554. Historical review-policy text
compatibility is fixed and its regression passes. One remaining warning is the
upstream Starlette/httpx test-client deprecation, not a runtime failure.

Engine199tests+81subtests passed. API parity65paths; source-verified saved-case
replay67cases/7608findings/0differences/0blocked; defaults equal; source rows
unchanged;0paid calls. Seven migrations applied/replayed only in isolated PG;
40source histories unchanged;40freshv2 imports exact. TypeScript/family assertions,
production webpack build,13static assets and authenticated production browser
configuration passed. Browser console has no error/warn entries. Synthetic
publishedv7/0documents preserved. Production web3100 session17759 and API8100
remain available; original3000/8000 stay on original code.

Local copied-database rollback to Step41 and restoration of current API passed.
New policy types require compatible workers; remote deployment/coordinated live
cutover remains outside the user-selected local-first target. No startup business
publication, case repinning, provider submission or original schema change.
All final test containers auto-removed. Retained136124-byte generated tracing
folder is locally excluded after automatic approval rejected cleanup; do not
retry deletion. Necessary backups retained. Full file list:STEP42_FILES.md.

Next publication gate: commit this accepted source; clean allowlisted export;
verify hashes/guards and included tests; expected-head public update from11520ed.


## Step42 delivery complete locally — 2026-10-23
Accepted source commit:b3116354fccedb0cc7885c92055c32ae28716e9d.
Public sanitized main:9cdc21cff658b83fad34578cc19aae8a47f16bf9,
parent11520ede47b0025d10232d3eead01819e7d887ee; expected-head update,
no force, independently verified by git ls-remote. Export354source files,
2361050bytes plus manifest; all hashes/sizes verified;0scanner blockers;
6export guards and127 included synthetic tests passed215.78s. Private history,
customer samples, credentials and browser evidence were not published.

Clean backend image:sqe-refactor-api:step42,
sha256:76ffe5a06361060266b827b729f8d4a1674cb1f82c6beebed2b2f03ba30a2825,
414499936bytes. First build hit transient package-index unavailability;
unchanged pinned versions resolved on retry. Fresh build succeeded; packaged
API health/auth/configv7/cases and pip check passed using a copied synthetic DB,
network disabled,0provider calls. Smoke container auto-removed. No dependency
versions were changed. Production frontend build/browser and standalone3100
remain accepted. API8100/original8000 healthy; original3000 code unmodified.

All local PLAN items complete. Remote server deployment and coordinated live
cutover are outside the explicitly selected local-first target. Business
configuration lives in versioned revisions; bootstrap/legacy catalogs preserve
historical compatibility. Authentication, bounded evaluator algorithms and
workflow state transitions intentionally remain code capabilities.

Recovery: read PLAN.md, FINAL_ACCEPTANCE.md, STEP42_FILES.md and this checkpoint.
No pending test/build/publication process remains. Preview web session17759 and
API container sqe-refactor-preview-api are intentionally running. Necessary
backups and accepted image/source artifacts retained; small cleanup-blocked
folders remain excluded. Never retry rejected deletion without renewed approval.
Documentation closure changes:docs/refactor/{PLAN,INVENTORY,CHECKPOINT,CHANGES,
VERIFICATION,STEP42_FILES,FINAL_ACCEPTANCE}. No runtime change after acceptance.


## Step43 started — operational local preview
User asked to move to the next phase and whether uploads already process.
Verified live preview: local file storage, local workflow driver,0documents,
0jobs, no Spider credential, no worker container. Saved connector model is still
3.8-flash-high. Therefore uploads can be accepted/stored but cannot finish
extraction. Original app's connector is configured with gemini-4-argon.
No credential value was read or printed; no model requests were sent.

Created compose.preview.yaml and docs/refactor/OPERATIONAL_PREVIEW.md: separate
project, persistent volume, API8100 and explicitly enabled worker profile, local
DB/files, bounded concurrency2, required external preview secret. Compose schema
validation passed. This prepares an operational stack; it has not started or
replaced the current preview. Original application remains unchanged.

Asked asynchronously whether to reuse the existing Spider connection (shared
billing/limits) or configure a separate one. Do not copy credentials or enable
paid processing until the answer arrives. Independent next steps: preserve
preview DB/files/secret; stage persistent state; cut over isolated API/worker;
verify readiness and run an explicitly authorized browser document test. Keep
provider quality distinct from job completion. Never use restored customer DB
for a worker. Existing Step42 local code acceptance remains complete; Step43 is
an operational enablement phase, not retroactive completion of paid extraction.
Files this step:compose.preview.yaml;docs/refactor/{OPERATIONAL_PREVIEW,
CHECKPOINT,CHANGES}. No runtime source changes.


## Step43 operational cutover — 2026-10-23
User explicitly approved reusing the original Spider-AI connection. Read the
source connector locally and re-encrypted its key for the preview inside the
source process; no plaintext credential printed or committed. Preserved the
preview APP_SECRET in private/phase43/preview.env (outside source Git).

Stopped and retained sqe-refactor-preview-api. Copied its SQLite database and
files to private/phase43 and persistent volume
sqe-refactor-operational_preview-state; database copy SHA verified;v7/0documents
preserved. Created sqe-refactor-operational-api-1 and worker-1 from the accepted
step42 image. APIhealthy on8100; worker uses local development queue/concurrency2
and independent state. Original app/worker/database/storage untouched.

Important preservation: packaged public datasets are empty examples. Exported
both actual preview references privately, explicitly registered them in the
isolated DB, and enabled registry reads. Saved Spider connection now uses
pct-prod-spider/pecut/gemini-4-argon. Configuration publication remainsv7.

Browser uploaded one synthetic PDF, QA_Preview_Riplay.pdf, through the real upload
form and confirmed Forex flow/grouping. Documentfc5ac23f-f7f3-4d39-ba41-5ea09c8af77f,
case628f0b46-b29c-441a-afd4-c7b83bbb66dd. Worker accepted the job; one classify
request c69ffa69-28e2-4686-9b38-ede6c13be841 is pending. Do not resubmit blindly.
No customer document sent. Do not claim end-to-end success before provider return,
extraction/SOP/report acceptance. Old preview retained for rollback; never run both
APIs on8100 or workers on the sameDB.

Created private operation helper:work/refactor/private/phase43/activate_preview.py;
backups pre-cutover.db/files/references.json and private env are not source files.
Changed source:compose.preview.yaml(DATASET_READ_MODE registry),
docs/refactor/OPERATIONAL_PREVIEW.md(preservation/operation instructions),
scripts/export_public_source.py(allow operational compose/runbook).
Six export guards and compose schema validation passed. No backend/frontend
runtime source changed; accepted image/backend tests remain applicable.
Next: await existing model request; inspect extracted values/crops/SOP/report;
verify persistent restart; record acceptance and publish only sanitized source.


## Step43 resumed with user-selected model — 2026-10-23
Argon classify request returned503 with structured model_temporarily_unavailable:
model busy, reset after30s. App correctly retained uncertain checkpoint and
recovery guard; no automatic paid replay. User replied to the retry question by
instructing use of pct-prod-spider/pecut/gemini-3.8-flash-high, then asked resume.
Updated only isolated connector through its application administration service;
credential retained/encrypted; original connector/model unchanged. Browser
recovery form recorded reason, explicit new-request authorization and resubmitted
one synthetic document. New classify requestada675cc-f253-4e55-8fa5-9c2a2a38ec0d
is running; current model confirmed3.8-flash-high. Do not blindly resubmit again.

Persistent restart acceptance passed: operational API/worker restarted;v7,
1synthetic document,2reference datasets retained; original uploaded source SHA
matches stored binary. Failed job remainedERROR and was not automatically
replayed after restart. All source files/HTTP evidence remain in private volume.
No backend runtime code change; no full regression repeat required for connector
configuration and operational compose/runbook/export allowlist changes.


## Step43 operational acceptance — 2026-10-23
User-selected3.8-flash-high succeeded: classify ada675cc-f253-4e55-8fa5-9c2a2a38ec0d
and extract b34e43f5-d8e3-4c06-939b-6f83bea5079c both HTTP200. One original Argon
classify attempt failed503. Three model submissions total; no automatic duplicate
replay. Synthetic documentCOMPLETED,10normalized fields; five expected text values
match exactly; absent customer signature observed correctly. Five localized PNG
crops decoded successfully. Browser field-crop display and dedicated review page
opened;0pending visual decisions,0human overrides. Crop UI also displays3internal
.complete metadata placeholders without images; polish follow-up, not3missing
source values. Keep that observation distinct from the5actual localized crops.

SOP workflow/report completed: latest reportv2
146ed0f6-c3c2-4361-91bb-01d85955410c.43eligible checks,4PASS/39FAIL,0pending.
Expected caseWAITING_DOCUMENTS/FAIL because onlyRIPLAY was uploaded and mandatory
application/LLD/invoice/signatures are deliberately missing. No failed rule was
approved merely to make test green. PDF/XLSX/JSON exports return200 and parse;
XLSX9sheets; every filename includes QA customer label. Older failure reportv1
remains historical, UI exposes latestv2. Source hash matches uploaded binary.

Second API/worker restart preservedCOMPLETED/10fields/2reports and jobstates
1COMPLETED+1historicalERROR, without another model submission. APIhealthy and
worker running on independent persistent volume. Original app remains running
unchanged. Stopped old preview container removed after verifying pre-cutover
backupSHA D2917B2065D4537189186318B5FE871EF5BD4818E607F0E670AEC3F3A8267DE5;
backup/private reference/env files and current volume retained. No volume or
original container removed. Rollback now requires recreation from retained backup,
not docker start of the removed old preview container.

Phase43 runtime enablement accepted. Real complete-customer UAT and remote server
rollout remain separate scopes; this synthetic test is not proof every future
model extraction is correct. Source changes are operational compose, runbook,
export allowlist and these records only; no backend/frontend algorithm change.
Next: commit source, refresh sanitized export, verify hashes/guards and publish
small delta to existing public main9cdc21c. Never publish private operational files.
