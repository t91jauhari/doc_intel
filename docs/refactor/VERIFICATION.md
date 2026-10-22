# Verification ledger

Baseline: Docker API, PostgreSQL, MinIO healthy; worker/web running at inspection. No refactored code activated.
Pending: baseline archive validation, actual restore rehearsal, regression suite and normalized-schema compatibility checks.

Record command purpose, exit status, timestamp and evidence paths for every stage. A readable archive is not proof of successful restore.
`nBaseline source commit created. PostgreSQL custom archive restored successfully with --exit-on-error into isolated network-disabled container; 21 public tables. Container stopped. Archive SHA256 recorded in checkpoint. API health confirmed ok. No object-storage backup yet; no refactor runtime verification claimed.

2026-10-22 implementation evidence:
- Docker run --network none with read-only source and temporary test storage: test_configuration_store.py 10 passed.
- Selected Account Opening, official rules, Forex v2, scoring, reviewer regression plus initial storage tests: 79 passed; one existing Starlette deprecation warning.
- Offline restored configuration snapshot: 40 revisions checked, zero semantic mismatches. Snapshot outside Git. No provider calls.
- No runtime activation or database migration performed. SQLite tests are not PostgreSQL migration verification.

Step 2: PostgreSQL contract tests + storage tests: 13 passed. Narrowed rollback exception assertion: 3 migration tests passed again. Rehearsal report: source_revisions_checked=40, publications=40, source_rows_unchanged=true, activated=false. Target mismatch rejects; invalid DDL rolls back journal and partial table; changed migration checksum rejects. Live API health ok. One existing Starlette deprecation warning.
