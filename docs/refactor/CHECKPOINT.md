# Refactor recovery checkpoint

Current status: Step41 accepted (private a469dd8; public11520ed). All528 backend tests covered; clean export126 passed. API8100/web3100 running. No live refactor activation.
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

## Step21 recovery checkpoint
Extraction service/contracts/adapters added; provider.run_provider remains compatibility facade. Requests copy pinned configuration and expose canonical hash; code-owned registry selects llama/spider-ai/fixture explicitly, unsupported IDs do not fall through to Llama. Malformed response/classification contracts fail; None response for classification-only remains valid. No new retry policy. Provider ProcessingIssue alias preserved. Pure configuration codec removes SQLAlchemy dependency from service hashing; store.fingerprint remains compatibility export.
47 provider/service/Spider recovery/config-store tests plus3 focused mocked Llama checkpoints passed. No live modifications or model calls. Next: explicit provider-state repository and concurrent checkpoint merge, then connector contracts, remaining API/SOP/dataset/report boundaries and acceptance/public-safe export/cutover.

## Step22 recovery checkpoint
SqlProviderState introduced behind ProviderStateStore protocol. Provider checkpoint/state_of compatibility helpers delegate through injected SessionLocal factory. Separate checkpoint transactions are intentional before external paid submissions; row locking prevents concurrent receipt merges losing data. Read/merge deep-copy JSON; missing documents and invalid serialization fail safely. Does not replace job claiming or add retries. Custom profile IDs now capped at50 to match actual document column; UI maxLength aligned.
10 state/custom tests including real PostgreSQL blocked concurrent writer passed;8 recovery/native reuse tests passed; TypeScript passed. Temp test schema absent, DB stopped, no orphan containers or model requests. Next: provider connector contracts and remaining R1 policies; R3 dataset/report registry and full verification/public-safe export/cutover. Native validation SKIPPED handling remains unresolved and must not be changed to unconditional PASS.

## Step23 recovery checkpoint
48 connector/provider/prompt/field-reprocessing checks passed; TypeScript passed. Both restored connector option records validated without credentials. Typed connector inputs/repository and server-derived advanced controls implemented; partial updates preserve existing model/scopes/options. Invalid stored settings fail closed, admin can repair. Legacy defaults captured in a manifest; actual configured model not changed. No paid calls or live writes.
Next: Step24 dataset registry in progress (new module/migration/tests not yet integrated or committed).6 synthetic dataset contract tests passed; runtime integration, explicit import and PostgreSQL immutability verification still required. Remaining R1/R2/R3/V1/C1 are not complete.

## Step24 recovery checkpoint
Step23 commit0d93df0. Dataset registry implemented with typed private imports, immutable IDs/digests/PGguards, explicit baseline import and bundled(default)/verify/registry rollout. No automatic startup import. Unknown references fail; family/flow selectors use catalog.22 tests plus TypeScript passed. Migration0006 applied only to isolated restore;40 histories unchanged.2 baseline references imported;67 case comparisons identical in read-only bundled-vs-registry rehearsal. Browser advanced connector persistence and catalog verified on synthetic preview; no published config change/model calls. Preview stopped/cache cleaned.
Next: remaining configurable complex/visual SOP/native field-validation outcome, dataset comparison policies and report read models, remaining service/root configuration contracts, full acceptance/public-safe history/cutover. Full refactor remains incomplete; live untouched.

## Step25 recovery checkpoint
Step24 commitfa812f0. Typed report_definitions stored through immutable configuration_entries; explicit defaults manifest and schema/context validation. Both renderers use pure projection; no score/layout changes. New family report editor supports sources/paths/fallback/timezone in unpublished draft.25 final report/storage tests and TypeScript passed;449 saved report rows equal to prior source. Browser UTC draft tested0 documents and discarded; publishedv7 restored/unchanged. Screenshot outputs/refactor-step25/report-mappings.png. Preview stopped/cache cleaned; baseline helper removed.
Next: native Spider SKIPPED field validation requires explicit configurable data policy, not automatic PASS; remaining complex/visual rules and root configuration/service contracts; comparison policy defaults; full suite/current extraction acceptance/public-safe Git history/cutover. Full refactor incomplete, live unchanged.

## Step26 recovery checkpoint
Step25 commit638fcdd. Configurable profile field_checks implemented across Spider/native/schema validation and selected rereads. Typed kinds/limits/choices/date/number/currency; no value rewriting; incomplete observations fail; native uncertainty/failure cannot be weakened. Visual fields excluded. Spider unchecked fields retainSKIPPED; configured fields feed real SOP results/points. Profile editor and workbook round-trip support; oversized XLSX settings fail clearly rather than truncate.32+39+69 overlapping regression selections passed, final25 field checks passed; TypeScript/browserNIK16 draft validated0 docs/discardedv7 unchanged. Preview/cache cleaned; isolated DB stopped.
Next: explicit migrated field-policy proposals for existing profiles (no automatic historical rewrite), remaining complex/visual SOP contracts and root/API boundaries, comparison/report presentation defaults, full acceptance/public-safe history/cutover. Live original unchanged; all phases not complete.

## Step27 recovery checkpoint
Step26 commitd28cb31. Typed account-policy grammar and explicit conditional source/value mappings implemented;6180 historical policies across40 revisions validate unchanged.30+45 overlapping focused tests and TypeScript pass. First shadow36 cases/5623 findings/108 convertedrules has0 state/score differences;18 older configs need known compatibility defaults, read-only compatibility rehearsal session28021 still running. Full503 backend suite session73332 running against frozen runtime: do not edit imported production modules during run. No result yet; do not claim full green. New conditional editor not yet browser-verified.
Next: finish running tests/rehearsals, inspect failures; public-safe source export (current Git history contains private fixtures so never push history); remaining comparison/report defaults/root/service contracts and full final activation acceptance. Live unchanged, no public push/cutover.

## Step28 active verification checkpoint
Step27 commit1687a1c. Conditional compatibility rehearsal finished:54 cases,7049 findings,162 proposedconversions,18 compatibility cases,0 mismatches/blocked, no writes. First full503 run stopped at outdated family dataset whitelist test after177 passes/7 PG skips. Updated test to reject malformed ID; added registered/unregistered publication guards. Affected20 tests passed51.32s. Remaining alphabetic test files inclusive test_document_families running session98361; runtime source frozen. PG migration tests still need final separate coverage for skipped7.
Public export guard/script and4 unit tests implemented. Audit284 files~2.22MB/192excluded0blockers; no output written yet. Never push old Git history. Export candidate must still be generated/inspected/built/tested and remaining phases completed. Isolated PG retained/running; preview stopped/cache cleaned. Live original untouched.

## Step29 active checkpoint
Step28 commit5f9024d. Public candidate work/refactor/public-source-candidate generated285files~2.23MB, source5f9024d, nohistory/privatefixtures/workbookvalues/screenshots;76 synthetic tests passed. Candidate is now stale versus current enum fix: do not publish it as final. Full suite second segment16 passed then exposed explicit Spider enum-revalidation no-op. Fixed audited alias application, native-only fixture provider clarified.40 enum/field checks pass12.37s. Remaining suite session7895 from test_enum_display inclusive still running (>45percent), runtime frozen. FinalPG7 tests pass. Production frontend build passes; start preview rejected by automatic approval review (blocked by policy only). Preview stopped/.next cleaned.
Next discovered acceptance risks to fix after frozen suite: (1) report bindings currently shared per layout; need per-family override so configuring another family cannot alter Forex mappings; (2) settings import creates project/data and storage directories unnecessarily, preventing truly readonly source mounting when explicit external DB/storage are configured. Then finish full coverage, updated clean export/build, remaining contracts/configuration inventory, isolated rollout/rollback/publication. Live remains healthy0.3.0, no public push/cutover.

## Step30 recovery checkpoint
Step29 commit5c5ae91. Broader enum->parse segment163 passes then native retry test failed because it mocked Llama while leaving Spider selected; fixture now publishes llama and focused retry passes. Family report mappings now isolated via family.report_definition, with field/context scope validation and legacy root fallback. Settings import write-free; explicit development initializer creates SQLite parent.26 report/family/latest and19 settings/report/writer/enum checks plus TypeScript passed. Current source stable, no tests running after session51580 completed.
Next: remaining suite tail from test_parse_evidence inclusive, then updated clean export including new enum/settings tests; candidate1 is stale. Final browser conditional/production smoke blocked by automatic review start rejection; no safe alternative attempted. Frontend production compile previously passed before family-only mapping edit; TypeScript passed afterward. Remaining architecture/configuration inventory still partial; no public push or live activation. Live healthy0.3.0.

## Step31 active checkpoint
Step30 commit540085d. External private JSON reference importer added (explicit org/expectedDB,50MBlimit, typed/no raw-value logging),11 dataset tests pass. Public exporter synthetic suite expanded; updated candidate not generated yet. Remaining test tail session39864 running; no full-suite green claim. New confirmed provider gap to fix after frozen run: full Llama extraction builds parse/extract options through engine.run.get_profile, so configured custom profile IDs can fail after upload/classification. Selected-field Llama already builds saved schema directly. Replace full request builders with provider-local profile-driven contracts and prove exact native payload parity/custom SDK wire. Per-family report and readonly-source fixes already tested/committed. Live unchanged, no public push/cutover.


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

Step41 verification continuation: the initial ordered backend run was deliberately interrupted after276passed/7PostgreSQLskipped (905.02s), then collection confirmed526non-Temporal nodes. Remaining nodes[283:] (243 nodes) resumed as three81-node shards, sessions69213/16173/47561. Each runner prefixes collected relative paths with /refactor/backend/tests; an initial path-only launcher attempt ran zero tests and was corrected before resuming. This partitions the remaining work without dropping the interrupted test. Temporal2passed49.40s (session34714 complete). PostgreSQL migration/provider-state11passed2.91s (session78070 complete), covering all8database-dependent checks separately. TypeScript passed. Preview state remains7/0 and liveAPIhealthy. No Step41 commit yet.
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


## Step42 verification resumed — 2026-10-23
Application separation now includes 43 operations, shared DTOs/projections,
transport-independent errors/access/upload ports, extracted crypto and a domain
compatibility facade. Bootstrap, configuration validation, revisions, routing,
auditing and case lifecycle have actual owning modules; consumers were rewired.
Saved-case replay checks the actual source import path and working directory:
67 cases,7608 findings,0 differences,0 blocked; default fingerprint equal;
source rows unchanged;0 provider calls and0 writes (session61238).

Full regression shards:0=143passed/1PGskip;2=216passed/7PGskips. Shard1 found a
real review compatibility bug: historical evidence.policy is a string label;
new typed visual logic attempted .get on it. Fixed by guarding dictionary type;
existing signature-review regression reproduces this defect. Shard1 rerun45803
is active (22 files,38 percent at last observation). Do not declare acceptance
until it finishes. PG11passed covers8 skips; Temporal2passed; engine199passed
plus81subtests. API metadata parity passed65paths after restoring the original
failure-summary description. No request/response behavior was changed.

Production webpack build and TypeScript passed; frontend family assertions
passed;6 export guards passed. Standalone production web3100 is running in
session17759 (dev89237 stopped deliberately); settings and13 referenced static
assets return200. Browser controls accepted visual/date/money editors and all6
Account Opening score groups; temporary draft discarded, preview publishedv7
and0documents verified. Browser navigation after switching servers hit an IAB
connection-error wrapper; do not claim production browser acceptance from HTTP
alone. Prior browser proof private/phase42/configuration-scoring.png retained.

Local rollback rehearsal: sqlite backup of synthetic preview only; accepted
Step41 API on8110 and current8100 both authenticated/readv7 successfully.
Temporary old API stopped/removed; current API restarted. First rehearsal launch
used the image working directory and accidentally loaded its bundled old app,
which refused startup; corrected --workdir /tmp to load intended baseline source.
Initial permissive shell output was invalid evidence; overwritten by successful
strict run. Neither attempt touched original app or paid providers.

Isolated PG0007 applied/replayed;40 old source rows unchanged;40freshv2 imports
round-trip. Docker engine restarted unexpectedly earlier during verification;
original containers auto-restored and healthy. No original files/schema/deployment
changed. Original remains ports3000/8000; isolated8100/3100. C free~10GB/O~7.5GB.
All temporary test containers auto-remove; existing blocked cleanup folders and
necessary recovery backups remain retained. No attempt to bypass cleanup blocks.

Next: finish45803; reconcile local PLAN/verification; commit accepted source;
fresh sanitized export and included tests; publish using expected public head
11520ede47b0025d10232d3eead01819e7d887ee. Never push private history.


Step42 runner correction: shard1 rerun passed102 tests including the historical
review regression, then its infrastructure-settings subprocess imported /app
bundled image code because the runner lacked an explicit working directory.
Only test_infrastructure_settings uses subprocess (rg inventory). Corrected runner
uses --workdir /tmp, and continues all unpassed nodes with XML-based selection;
session6831 writes backend-1-tail.xml. Retain backend-1.xml as102passing evidence;
do not count the harness failure as a product defect or a passing check. Shards0/2
use checkout code through conftest; no other subprocess test files exist.

Production browser recovery: old tab10 remained bound to a stale connection-error
page. A fresh same-origin tab11 opened the production standalone build correctly.
Authenticated settingsv7 and Account Opening's6 score categories loaded; corrected
family punctuation verified. Screenshot private/phase42/production-configuration.png
saved and inspected; tab11 marked deliverable. Old error tab close was rejected
by its data-URL wrapper; no bypass attempted. This supersedes the earlier browser
acceptance limitation. Production server17759 remains running on3100.


Cleanup record: production standalone tracing created a136124-byte directory at
this checkout's sourcecode/ (ordinary files; no reparse links). Its removal was
rejected by automatic approval review: blocked by policy. It remains retained
and is excluded through local Git info/exclude; no retry or alternate deletion.
This is separate from the real original app at work/sourcecode. Active standalone
node_modules is a read-only-use symlink to shared dependencies; never delete or
modify that target. Generated tracing files are not part of STEP42_FILES.md or
source publication. Browser tab11 reports no error/warn logs.


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


## Step43 delivery complete — 2026-10-23
Accepted operational source:e4a83e469511023a193980f4ab52fc69cd442258.
Public main:c1e41c465ecc7d5a6582cb5102021e15a3bea79e, independently verified;
parent9cdc21c, expected-head/non-force update. Fresh export356files/2365030bytes
plus manifest;0scanner blockers; all hashes verified;6guards passed. Public delta
onlycompose.preview.yaml,OPERATIONAL_PREVIEW.md,exporter and manifest. Backend,
frontend,engine hashes unchanged from fully verified Step42, so no redundant full
suite run. No private operational data or Git history published.

Preview3100/API8100/worker operational with persistent independent state;
modelpct-prod-spider/pecut/gemini-3.8-flash-high. Synthetic live acceptance and
restart persistence passed; no model requests remain running. OriginalAPI8000
healthy, original app unchanged. Browser tab11 left at synthetic case, screenshot
private/phase43/completed-preview.png. All incomplete-package failures remain
correctlyFAIL; no fabricated visual approvals. Full evidence:OPERATIONAL_ACCEPTANCE.md.

All current local/operational phases accepted. Subsequent scope is full real
customer UAT or server-specific production deployment; neither is claimed done.
Obsolete isolated preview container removed; recovery backup/private env/reference
files and current persistent volume retained. Do not rerun one-time activation
helper against the already migrated preview. API/worker containers intentionally
run with restart policy; frontend standalone session17759 remains active.
Closure files:docs/refactor/{PLAN,CHECKPOINT,CHANGES,VERIFICATION,
OPERATIONAL_ACCEPTANCE}. No runtime algorithm changes in this closure.

## Step44 in progress — shared infrastructure and legacy parity
User authorized reusing existing Temporal/MinIO while finishing backend parity.
Original API/web/worker/database were not changed or restarted. Preview now uses
shared service instances with dedicated namespace sqe-refactor-preview, queue
sqe-refactor-preview-documents, scoped IAM user and separate bucket. SQLite preview
state remains isolated on its persistent volume; production requires PostgreSQL.
18 objects / 1765334 bytes copied and SHA verified; original bucket access denied
for preview credential. Private pre-migration database/environment backups and
receipt retained in ../private/phase44. Never rerun migration helper blindly.

Runtime changes: settings.py namespace setting/validation; worker.py passes selected
namespace; field_evidence.py excludes raw/complete wrapper metadata from crops.
Four focused regression additions. Compose preview uses shared external services;
production compose exposes namespace. Image sqe-refactor-api:step44 running healthy.
Focused12 tests passed; Temporal3 passed; PostgreSQL11 passed. Full backend shards
running sessions3404/57415/18802, JUnit ../private/phase44/backend-{0,1,2}.xml.
No runtime edits while these tests run. Legacy API65 operations all retained;
9 added; three schema differences under review. Legacy tests219 unchanged,
10 adapted,7 provider-specific test names removed: verify replacement coverage.
Browser crop refresh submitted for synthetic case628f0b46-b29c-441a-afd4-c7b83bbb66dd.
Next: verify crops5 (not8), actual Temporal workflow completion and retained exports;
finish contract/capability matrix, full tests, checkpoint/file inventory, commit,
sanitary export/build/publication with expected public headc1e41c4. Real full-customer
UAT remains distinct from backend parity; remote deployment deferred by user.

## Step44 live shared-service results
Original source PDF and five actual crop objects were read from shared MinIO and
SHA verified. Browser crop refresh removed three .complete metadata placeholders.
One authorized selected-field provider rerun completed for document_place; existing
other fields retained. Shared namespace reports one COMPLETED DocumentWorkflow
and two COMPLETED CaseSOPWorkflow executions, all on isolated task queue. Current
synthetic reportv4; incomplete package failures remain unchanged. That rerun exposed
parent-wrapper vs .raw duplicate evidence rows. Added bounded fix and regression;
affected evidence/spatial/field-rerun/prompt suite session95896 currently running.
Full backend initial pass:144+187+216=547 passed,8 PostgreSQL skips; separate PG11
covers those8; Temporal3. Unique coverage558 before final new crop test,559 after
its affected suite passes. No engine/frontend changes; previous evidence retained.

## Step44 complete — 2026-10-23
Source commit3a90a46aa3fe9a6925a855f08442990ba5ac68c0. Final targeted evidence,
spatial,field-reprocessing,prompt suite36passed, including extra wrapper crop test.
Unique backend coverage559:547fullshard passes+8database cases covered byPG11+
3Temporal+1newwrapper regression. No outstanding test failures. Engine/frontend
unchanged; accepted Step42 evidence applies. Six export safety guards passed.

Fresh sanitized export356files/2368687bytes plus manifest;0blockers; every manifest
hash verified. Final image9aa5bcc27decdb0f11dfc103df8df1eb6cd21de5cbae573cf5ff7234a3b0d52a
built from export. All247backend/app and engine files in running API match manifest.
API/worker both sqe-refactor-api:step44-final healthy/running; frontend3100 retained.
Shared Temporal namespace:DocumentWorkflow1+CaseSOPWorkflow3 COMPLETED. Selected
field request completed; original source SHA and5crop SHAs verified after restart.
HTTP source/page and PDF/XLSX/JSON report exports passed200/parse. Browser final
refresh shows5available crops (no .complete or parent/.raw duplicates), latest
reportv5. Deliberately incomplete package remains4PASS/39FAIL; no fabricated review.
Screenshot ../private/phase44/corrected-crops.png. No further paid model requests.
Original API/web/worker remain running unchanged. Preview state/credentials/backups
remain private. Two unused intermediate images created this phase removed; final
image and necessary baseline/recovery artifacts retained. Temporary tests --rm.

Public mainc1f4235f2ea61aec3824125d21bf62f2ae105591, independently ls-remote verified;
parentc1e41c4, non-force expected-head update. Delta8files including manifest;
no private history/customer documents/references/secrets included. No PR created.
All backend refactor/local capability acceptance work is complete. Full live
customer dataset accuracy evaluation is separate and not claimed completed;
remote production deployment awaits user server details. Never rerun one-time
migration helper blindly. Recovery evidence and file list in STEP44_FILES.md,
LEGACY_CAPABILITY_PARITY.md,VERIFICATION.md. No background tests/model jobs remain.
