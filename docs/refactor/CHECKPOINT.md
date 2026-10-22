# Refactor recovery checkpoint

Current status: STEP15_CONFIGURATION_READS_VERIFIED; M1 complete in isolation. Docker restart recovery in progress; no refactored runtime activated. See final checkpoint below.
Canonical tracking: this directory. Sibling tracking directory contains only a pointer after baseline setup.

Live application: work/sourcecode/document-platform; ports 3000/8000; API health ok. Never deploy isolated code to this stack during development.
Isolated implementation: work/refactor/document-platform. No live .env, storage or node_modules copied.
Baseline source commit: 9925098d2b504e95edc1aeae54d41c30fb399207.
Database archive: ../../../../refactor/backups/baseline-2026-10-22.dump (resolve from workspace: work/refactor/backups).
Archive SHA256: 6ADA033201D84393094A40D3A6693FC62A4D8224AABB721D6E28735FBC2221E4.
Restore rehearsal: passed pg_restore --exit-on-error in network-isolated sqe-refactor-baseline-db; 21 public tables. Container stopped and retained. Object storage not backed up yet; no cutover permitted.

## Resume
1. Read PLAN, INVENTORY, DECISIONS, VERIFICATION and MIGRATIONS here.
2. Inspect git status/log and actual Docker state; reconcile incomplete commands.
3. Never run copied compose.yaml unmodified: its project name and ports match live stack.
4. Next: inspect dependency/migration setup; capture isolated regression baseline; implement typed configuration publications and additive schema migration in isolated environment.
5. Preserve all original Config revisions/case pins; test semantic import/compile round trip before runtime replacement.

Update this file after each verified unit. Distinguish implemented, tested, migrated and activated. No live schema/data changes have been made.

## Repository checkpoint
Remote origin: https://github.com/t91jauhari/sqe-bic-docplatform.git
Remote inspection: reachable; ls-remote returned no refs (appears empty).
No push performed. Local baseline history contains customer datasets, PDFs, workbook and screenshots. Do not push this history to a public remote. Prepare a clean publication history excluding customer artifacts and replace required fixtures with synthetic equivalents. Scan source literals and operational scripts too; excluding files alone is insufficient.
Next action: public-export inventory and synthetic dataset compatibility, then isolated regression baseline and configuration contracts. GitHub CLI unavailable; Git remote reads work. Write authentication remains unverified.

## Implementation checkpoint — 2026-10-22
Status: FIRST_STORAGE_SLICE_TESTED; not migrated or activated.
Implemented: app/configuration/store.py (separate publication/entry tables, caller-owned transactions, idempotent revision import, digest-checked compatibility reconstruction); offline verify_snapshot command. This is transitional persistence, not final normalized entities or typed policy implementation.
Verification: 10 focused tests passed. Selected existing regression suite plus first 9 new tests: 79 passed in 143.79s. All 40 historical configuration revisions exported from restored backup: checked=40, mismatches=0, activated=false. Live health remains ok.
Private snapshot: work/refactor/private/configurations.json; never commit or publish. Restored database container stopped again.
Next: explicit versioned additive migration tested on isolated PostgreSQL, typed identity/rule policy contracts and read-only shadow evaluation. Public export sanitization remains unfinished; no push.
Important: no background process remains after these completed checks. Resume from this checkpoint, not from an assumption that the full refactor is complete.

## Step 2 — explicit PostgreSQL migration (2026-10-22)
Implemented and tested on isolated restored database only; live schema/runtime unchanged.
Created:
- backend/app/configuration/migrate.py — target guard, transaction, advisory lock, checksum journal.
- backend/app/configuration/migrations/0001_publications.sql — additive publication/entry tables.
- backend/app/configuration/verify_postgres.py — repeated import and source-row integrity checks.
- backend/tests/test_configuration_migrations.py — PostgreSQL wrong-target, transactional rollback and changed-checksum tests.
Modified:
- backend/app/configuration/README.md — migration operations and limitations.
- docs/refactor/CHECKPOINT.md — recovery state.
- docs/refactor/MIGRATIONS.md — isolated execution record.
- docs/refactor/VERIFICATION.md — test evidence.
- docs/refactor/CHANGES.md — per-step file inventory (created this step).
Verification: 13 focused tests passed; tightened exception assertion rerun 3 passed. 40 historical revisions imported/reconstructed twice; zero differences; original configurations/cases unchanged. Live health ok. Isolated database stopped. No push/activation.
Next: typed configurable identity bindings and generic rule policy contracts; test config-controlled behavior before replacing grouping paths.

## Step 3 — configurable identity policy (2026-10-22)
Status: implemented/tested in isolated source only. No configuration or runtime activated.
Created: backend/app/configuration/identity.py; backend/tests/test_identity_policy.py; docs/refactor/IDENTITY_CONFIGURATION.md.
Modified: backend/app/grouping.py; backend/app/domain.py; backend/tests/test_configuration_store.py; docs/refactor/CHECKPOINT.md; docs/refactor/CHANGES.md; docs/refactor/VERIFICATION.md.
Behavior: explicit profile+normalized-field bindings, optional extraction-schema wrapped path, exact-token/compatible-initial policy, publish validation. Missing policy preserves legacy mapping; explicit empty bindings disable check. Existing filename grouping unchanged. Policy currently persists in publication extensions; dedicated normalized binding table and UI pending.
Tests: 42 passed, 1 deselected; added policy persistence test passed separately. Excluded test_preview_and_upload_use_same_plan failed identically on untouched baseline commit 9925098 (expected 1 document, actual 3); pre-existing issue, not resolved or hidden. Baseline-regression worktree retained for reproduction. Live health ok.
Next: dedicated binding persistence/migration and saved-case shadow comparison, then generic SOP policy contracts. Public sanitization/push still pending. All commands finished; no background processing implied.

## Step 4 — 2026-10-22
Dedicated identity policy/binding tables implemented. Migration 0002 rehearsed only on isolated sqe_refactor. New imports validate/store identity policy separately; empty/absent semantics and digest verification retained. Legacy declarative mapping is shadow/migration input, not runtime defaults.
Tests: 35 focused passed; expanded PostgreSQL migration suite 4 passed. 40 historical publication round trips unchanged; 67 saved cases compared read-only with zero mismatches and zero configuration errors. Live API healthy; isolated DB stopped; no running commands, public push or activation.
Changed-file inventory and commit message: CHANGES.md Step 4.
Next highest priority: generic SOP policy contracts/evaluators and explicit family membership; preserve source versions and compare saved findings. Identity UI/publication workflow and public export sanitization remain pending. Earlier baseline upload assertion remains unresolved.

Step 5 progress: optional rule_scope validated at publication and used for explicit family membership. Generic comparison contracts implemented without runtime dispatch. Focused tests 44 passed; added publication-path test separately 1 passed. Restored read-only scope comparison: 40 config revisions, 112 flows, zero differences. Current transaction-flow regression run pending final result at time of this entry. Isolated DB stopped, live API health ok.
Final Step 5 result: transaction-flow regression + initial comparison/scope contracts 18 passed in 73.15s; added publish-validation test 1 passed separately. Combined identity/storage/contracts selection 44 passed. No new failures. No pending commands. Next: dedicated membership persistence and generic evaluator integration with saved-SOP result checks. No live publish/deployment.

## Step 6 recovery checkpoint
Status: dedicated family-rule tables implemented and tested on isolated PostgreSQL only.
0003 applied/replayed with no changes on replay. All 40 original revisions match; case/config rows unchanged. 51 focused tests passed. Read-only generic-vs-current comparison: 67 cases, 61 supported decisive text outcomes, zero differences. Unsupported 5858/unresolved 55 occurrences skipped, not certified. Remaining evaluator integration must preserve uncertainty/applicability/review and scoring; do not replace complex rules on this subset evidence.
Created/modified file list: CHANGES.md Step 6. Live health ok. Isolated DB stopped, all commands complete. No background work, live migration, publication, deployment or push.
Next: wire explicit generic policies into evaluator with typed applicability and uncertainty handling, add outcome/report integration tests, then expand shadow coverage. UI, final configuration tables and public sanitization still pending. Pre-existing upload dedup assertion remains unresolved.

## Step 7 recovery checkpoint
Implemented optional generic_sop_rules runtime dispatch, schema/family validation, standard finding evidence, applicability and uncertainty semantics, scoring and report integration. Definitions use configuration_entries section rows; no new migration needed. Existing configurations without this key unchanged. No automatic conversion or new UI.
Tests: 64 regression tests passed; final focused selection 39 passed. Integrated saved-result shadow comparison 61 supported decisive outcomes from 67 cases, no differences; skipped complex/unresolved counts remain 5858/55. Excel integration tested after correcting incomplete synthetic fixture metadata. Live healthy; DB stopped; no pending commands.
Created/modified files: CHANGES.md Step 7. Next: convert selected existing rules explicitly with audited configuration upgrade, expand equivalent outcomes/conditional policies and add configuration editing UI. Hard-coded legacy paths, native validation SKIPPED issue, baseline dedup assertion and public export remain unresolved. Do not claim full refactor complete or pushed.

## Step 8 recovery checkpoint
Draft conversion API/CLI and read-only full-case verifier implemented. Rule IDs, enabled state, source and categories retained; rule_order preserves evaluation/report ordering. Selected unsupported policies rejected; proposals validate before return. No source mutation/publication or startup conversion.
Private review draft: work/refactor/private/comparison-upgrade-v40.json; AO_SYSTEM_7 and AO_SYSTEM_13, version40 source. Never publish private file to GitHub. Validation basis hash stored in draft. No configuration activated.
Verification: 45 focused tests passed. Shadow with saved contexts: 36 cases/5623 ordered findings/144 per-case-version conversions, zero state/scoring differences. 18 cases blocked by current validation (sop_review_bypass missing/nonboolean); 13 cases no supported rules. Do not claim all 67 converted. Old configurations intentionally not silently defaulted.
Live healthy; isolated DB stopped; all commands complete. Next: configuration-service upgrade preview API and editor, with explicit current-version precondition; compatibility handling for legacy validation; remaining evaluator/prompt/provider hard coding and public sanitization still pending. Complete change inventory: CHANGES.md Step 8.

## Step 9 recovery checkpoint
Upgrade service and administrator-only preview router added. Settings offers family-filtered preview/apply-to-draft and basic generic comparison editing; converted rules remain available in flow selectors. Draft rule order reconciles add/delete. No new publication or migration from preview API.
19 backend API/upgrade/runtime tests passed; final TypeScript check passed. Browser smoke on fresh synthetic SQLite preview (3100/8100): AO_SYSTEM_7/13 previewed, applied to local draft, normalization edited, published version remained 7. No publish. Screenshot outputs/refactor-step9/comparison-editor.png. Preview API container retained stopped; Next dev session ended. Live API health ok. Next-generated frontend AGENTS/CLAUDE retained; dev next-env change restored. Dependency junction is local ignored state, not a portable dependency setup.
Next: legacy configuration compatibility upgrades, advanced rule/family/identity editing, provider/prompt/service separation and public-safe export. Full schema normalization, remaining hard-coded native profile catalog and dataset/report behavior still pending. Do not claim full refactor complete/deployed/pushed. Canonical per-file inventory: CHANGES.md Step 9.

## Step 10 recovery checkpoint
Explicit compatibility release and preview service/routes implemented. Seven formerly absent required settings can be added only by selecting missing keys; existing values cannot be replaced. Published/historical versions are never rewritten. Review bypass false. Boolean validators now reject 0/1. No UI compatibility editor yet.
Verification: compatibility suite 13 passed; API/conversion/initial compatibility selection 16 passed. Read-only saved-case rehearsal with --compatibility: 54 eligible cases, 7049 ordered findings, 216 rule conversions across case versions, zero mismatch, zero blockers, compatibility_cases18. Remaining13 have no supported conversions. This resolves prior 18-case validation blocker in proposals, not by modifying history.
Live health ok. Restored DB stopped; no pending jobs/commands. Files listed in CHANGES.md Step10. Next: compatibility review UI/advanced generic field editing and final service/configuration boundaries; public-safe export still pending. Full refactor remains unactivated and unpushed. Native validation SKIPPED and baseline upload dedup assertion remain separate outstanding issues.

## Step 11 recovery checkpoint
Schema-derived field options API plus comparison field/applicability editor implemented. Admin/version checks retained. Schema paths update with normalized bindings. Context choices come from existing backend registry (still code-based). Visual-region text and self-comparisons rejected. Numbers/arrays excluded. Existing native profile catalog remains fixed; this phase does not enable arbitrary new extraction profiles.
Tests: final43 focused passed,5 API passed, TypeScript passed. Isolated browser draft source ektp.name versus opening-form name, customer_type=INDIVIDUAL; read-only Test settings accepted but preview DB had0 documents. No outcome coverage claimed for browser. Screenshot outputs/refactor-step11/field-applicability-editor.png. No publication or live changes.
All preview processes stopped, live API healthy. Changed files in CHANGES.md Step11. Next priorities: dynamic profile/provider contracts and context registry; public-safe export; remove startup policy mutation and wire normalized publications into publish service. Complex SOPs/remaining datasets/reports still require refactor. Do not mark overall complete.

## Step 12 recovery checkpoint - current plan point M1
Interactive publish endpoint now uses transactional application service. CONFIGURATION_STORAGE_MODE defaults legacy; explicit dual writes Config+normalized rows+audit atomically after migrated-table/history checks. No deployment env changed. Historical config IDs/case pins retained and request data copied before instruction compilation.
Tests:17 publication/API/flow passed (142.54s);5 PostgreSQL migration tests passed (0.72s); final1 source-immutability/prompt compilation test passed. Restored PostgreSQL rehearsal proposed41, exact round trip then rollback; original config/cases/publications/audit unchanged. Live health ok. DB stopped; all commands finished.
Plan table rewritten in PLAN.md so status is visible. M1 remains partial: startup seeds, profile guidance and other writers bypass service; normalized read authority/DB immutability pending. Next: inventory/migrate remaining configuration writers and add normalized read verification, without startup overwrite. R1 complex policies, R2 provider boundaries, R3 datasets/reports, full V1/C1 and public export remain outstanding. Per-file list: CHANGES.md Step12.

## Step 13 recovery checkpoint — host resource blocker
All production configuration inserts now use persist_revision, preserving caller transactions and per-upgrade validation. Guidance append, bootstrap and all legacy seeds honor dual mode. API and worker startup no longer seed business configuration. Explicit development initializer with expected-database guard replaces startup upgrades. Test setup explicitly initializes its isolated state.
Verification completed: 4 new writer/startup/dual-guidance tests passed; broader publication/guidance/account suite 26 passed and 1 outdated prompt-length fixture failed. Fixture corrected to account for spatial instruction compilation; final targeted rerun could not finish because Docker control stopped responding. Do not claim final suite green. Full backend AST parse passed.
Storage incident: C: filled during a read-only logical MinIO backup (233175040-byte incomplete archive). Incomplete archive removed; no live storage writes. Failed file edit restored from Git before applying intended fixture correction. Isolated frontend .next cache moved reversibly to O:/CodexBackups/document-platform/preview-next-cache, recovering about 300 MB. Source and database archive unchanged. Live API /api/health returned ok/version0.3.0 after incident.
Docker clients for targeted rerun/backup/inspection were terminated after stalling. Docker ps still timed out after 8 seconds. No Docker daemon restart attempted. An isolated test container may remain; reconcile Docker inventory after recovery before launching more tests. No background completion is implied.
User asked asynchronously to free 5–10 GB on C:. O: is a local fixed DATA drive with about 8 GB free; backup retry did not pass inventory, so no completed object backup exists. Do not cut over.
Resume: recover host/Docker responsiveness without disturbing live app; rerun corrected prompt-length test and full affected suite, verify startup initialization CLI, then normalized read authority, remaining policy/provider/report refactor and full acceptance. Every earlier pending plan item remains pending; do not mark all steps complete. No public push or live activation.

Step14: guarded backup utility and3 offline integrity tests added. Step13 committed d03877a. B0 remains partial: no verified object archive. Full file inventory in CHANGES. No ongoing host commands; Docker container inventory must be reconciled after recovery.

## Step15 recovery checkpoint
Disk recovered by user: C: approximately14 GB free. Direct npipe docker_engine_linux endpoint works; standard desktop proxy had stalled. Clean temporary Docker CLI configuration and Linux host mount paths were used, with --rm runners. Fresh22 focused tests and52 broader account-opening/field-reprocessing/platform tests passed. Source must remain frozen during runs; mixed-module run discarded, not hidden by fallback code.
Configuration repository now handles latest/pinned reads throughout case processing, extraction, datasets, grouping repair, review and API. Snapshot payloads are copied. Explicit legacy(default)/verify/normalized modes; verified modes require dual writes and imported history.40 PostgreSQL revisions and67 case pins checked in a read-only transaction with0 differences. Publication rehearsal exact/rollback/original-rows-unchanged. Client exit stalls after some successful aggregates were control-plane failures; no configuration flag activated. M1 implementation verified in isolation, activation remains C1.
Object baseline backup completed:7655 objects, SHA25609e18e95aea8c9dc1910070b8652d7573fe70f82a14f44cc205682a7573b3d5c, O:/CodexBackups/document-platform/objects-2026-10-22.tar.gz. No live objects modified. No duplicate backup created. Snapshot times differ; coordinated cutover capture still required. User requested cleanup after large actions.94 MB preview cache on O: retained only because recursive delete was rejected by automatic policy; test containers --rm, no new images built.
User explicitly authorized Docker Desktop restart. Normal desktop restart timed out stopping processes. Stuck Docker GUI/backend/build processes stopped, Desktop reopened hidden. Verify engine readiness and live API/frontend/worker health before further tests; do not rebuild or replace current app with refactor. No public push.
Next: finish restart verification; D1 database immutability; remaining R1/R2/R3 contracts/services/configuration; final V1/C1. Full refactor remains incomplete. Exact files in CHANGES Step15.

## Step16 recovery checkpoint
Docker restart completed: original API/worker/web/Postgres/MinIO/Temporal healthy, no source or image replacement. Standard Docker control works again. Step15 commit fee8631. No orphan test containers; preview and baseline containers are intentional retained fixtures. Old94 MB preview cache cleanup remains policy-blocked.
PostgreSQL immutability migration0004 implemented/tested on isolated restore only.6 migration tests passed, including direct UPDATE/DELETE/TRUNCATE on7 tables and late inserts across5 child tables. New revisions/idempotent imports valid.40 histories round-trip; original configs/cases unchanged. Publication rehearsal proposed41 and rolled back exactly. Remaining D1 entities/typed contracts and R1/R2/R3/V1/C1 still incomplete; no public push or activation. Next: remaining runtime defects and policy/provider/report configuration. Source file list in CHANGES Step16.

## Step17 recovery checkpoint
Legacy refresh no longer references undefined profile-upgrade locals or edits configuration. New tests verify READY/missing-document outcomes, unchanged pinned payload and idempotent reports. Grouping baseline assertion corrected to reflect distinct fixture bytes; separate identical-content test verifies real deduplication.17 tests passed; final strengthened2 legacy tests passed. Removed clean obsolete baseline-regression worktree; baseline commit still retained. No live changes. Next: configurable context contracts and remaining R1/R2/R3.

## Step18 recovery checkpoint
Shared typed context registry implemented end to end: dedicated context-definition table/migration0005, enum/text/digits/document-reference contracts, family/profile bindings, limits and reserved audit keys; default bootstrap includes explicit definitions. Legacy absent uses versioned manifest; explicit empty stays empty. Rule validators/editors and case annotation API/form use registry; catalog case_id is authorized and resolves pinned config. New UI lets admins add/edit labels/types/options/length/profile bindings in unpublished family draft. Existing cases keep prior choices after later publication, verified by API test.
Tests:39 focused,43 regression,6 PG migrations; final strengthened24 selection passed. TypeScript passed. Browser synthetic preview added enum and tested draft; version7 remained published and0 documents. Screenshot outputs/refactor-step18/context-editor.png.40 PG historical round trips and rollback rehearsal unchanged. No live publication/model calls.
Cleanup: Next session28736 stopped; preview API/database stopped; temporary browser closed; next-env restored; generated frontend/.next removed via scoped git clean after dry-run. --rm runners. No new images. Old O:/CodexBackups/document-platform/preview-next-cache retained due automatic deletion-policy rejection. Verified841 MB object archive and142 MB database baseline retained. Next priorities: dynamic profile contracts, complex policy handlers, provider boundaries, datasets/report configuration, full acceptance and public-safe publication. Full refactor not complete.

## Step19 recovery checkpoint
Custom profiles now register with explicit validation_adapter=schema, saved schema/label/classification/suffixes, family and flow bindings. Native adapter contracts retained; cannot replace native adapters or remove the required native compatibility catalog yet. Structural adapter executes types/required/enum/unknown-field checks, missing required values fail, incomplete wrapped text remains uncertain. Rejects unexecuted schema constraints, unsupported policy keys and nonfinite values. No authenticity/business-policy inference. Saved-schema access removes eager native get_profile lookups across API/reprocessing; generic validation supports both providers without changing native normalization.
UI Add document profile creates unpublished starter profile in selected family; schema fields/instructions editable. Custom end-to-end mocked extraction -> SOP comparison -> report succeeded, and selected field retry preserved other field and saved guidance to profile.20+5+10 tests passed in described overlapping selections; extended pipeline1 passed. TypeScript and browser0-document draft validation passed. Screenshot outputs/refactor-step19/custom-profile.png. Preview stopped, Next cache removed, no orphan runners or new images.
Next: create new generic comparisons directly in UI, then remaining complex policies/provider services/dataset/report registry/full verification/public-safe export/cutover. All live code/data unchanged. File inventory CHANGES Step19.

## Step20 recovery checkpoint
New text comparison creation available directly in SOP configuration, using family schema-derived fields including custom profiles. Distinct bindings, unique IDs, schema paths, rule_order and explicit scope updates preserved. Field options load without existing generic rules; context changes refresh choices; requests debounced250ms. Nested label ambiguity fixed with full paths.
TypeScript passed. Browser synthetic draft created name comparison, validated, selected in flow and validated again; publishedv7 unchanged,0 documents. Screenshot outputs/refactor-step20/new-comparison.png. Preview API/Next/tab stopped and .next removed; --rm tests leave no orphan runners. No cloud calls or live changes. Next major areas: complex/visual policy contracts; provider/service boundaries; dataset/report registry; final full acceptance, clean public history and cutover. Full refactor still incomplete.
