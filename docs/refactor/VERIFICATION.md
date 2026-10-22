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

Step 3: identity/grouping/storage selected tests: 42 passed, 1 deselected in 56.45s; new policy persistence test separately 1 passed. Full selection initially 37 passed/1 failed after wrapper fix. Failure test_preview_and_upload_use_same_plan: expected one deduplicated document but received three. Independently reproduced on pristine baseline 9925098 with identical assertion. Keep as pre-existing unresolved regression, do not claim whole suite green. Live API health ok. No model calls or live writes. No historical-case shadow verification claimed yet.

Step 4 evidence: focused identity/storage/migration suite 35 passed. Added PostgreSQL dedicated-binding import test; complete migration suite 4 passed. verify_postgres: migration 0002 applied, replay empty, 40 source revisions/40 publications, source_rows_unchanged true. shadow_identity in READ ONLY transaction: 67 cases checked, mismatches 0, configuration_errors 0. Earlier attempt found 54 schema-wrapper errors; fixed compatibility proposal to validate wrapped/plain representations and reran successfully. Final rerun after deep-copy safeguard again zero differences/errors. Live API health ok. No extraction requests.

Step 5: 44 focused identity/storage/contracts tests passed. Transaction-flow regression + initial rule contracts: 18 passed (73.15s). Additional publication validation test: 1 passed. Read-only scope shadow comparison 40 revisions/112 flows, mismatches=0. No generic SOP outcome-equivalence claim: evaluator is not connected yet. Known prior upload baseline assertion remains unresolved. Live API health confirmed ok.

Step 6: 51 focused tests passed in 3.49s, including Postgres migration, policy/membership round trips, empty selections, order and tamper detection. Restored migration report: 0003 applied, replay empty, 40 revisions/40 publications, source_rows_unchanged true. Read-only shadow_comparisons: cases_loaded 67, outcomes_checked 61, mismatches 0, unsupported_rules_skipped 5858, unresolved_results_skipped 55. Generic component remains unconnected; broad SOP equivalence not claimed. Live health ok; isolated DB stopped.

Step 7 evidence: 64 passed in 129.72s (new runtime initial tests + existing official Account Opening/Forex/scoring/transaction flows). Final focused generic/storage/contracts 39 passed in 5.66s, including Excel SOP Details finding assertion. Initial Excel test failed due to missing filename/raw/overrides/sha256 in synthetic fixture; fixture corrected, renderer unchanged. Integrated runtime shadow: 67 cases loaded, 61 outcomes checked, mismatches 0; unsupported 5858/unresolved 55 skipped. Assertions now compare result, eligibility and category. Generic compare is DATA-only, uncertain REVIEW issues fail, unknown applicability fails, explicit non-applicability excluded, duplicate/missing docs fail. Live health ok, isolated DB stopped.
