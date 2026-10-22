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
