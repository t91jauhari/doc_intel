# Refactor recovery checkpoint

Status: BASELINE_COMPLETE; configuration schema proposed. No refactored runtime code activated.
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
