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
