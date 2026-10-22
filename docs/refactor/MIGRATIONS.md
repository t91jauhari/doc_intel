# Migration ledger

No live migrations executed. No refactor configuration activated.
Baseline database dump initiated; storage backup and restore rehearsal pending.
All future entries require migration identifier, source/target version, environment, status and rollback procedure.
`nBaseline restore rehearsal complete in disposable isolated PostgreSQL. No application migration executed. Restored container retained stopped.

Step 2: 0001_publications applied to sqe_refactor in stopped-after-test sqe-refactor-baseline-db only. Replay applied zero migrations. Journal checksum recorded. 40 publications imported twice without replacing originals or case pins. No live migration. Rollback: old application remains authoritative; additive tables can remain unused. No destructive downgrade.

Step 4: 0002_identity_bindings applied on sqe_refactor only. Migration replay empty. Configuration history and case rows verified unchanged; no new live tables. Restored DB retained stopped. Additive rollback remains old runtime plus unused tables.

Step 6: migration 0003_family_rule_membership applied only to sqe_refactor. Replay applied none. Historical publications 40, source rows unchanged. Dedicated new-policy import tested in temporary PostgreSQL schema and SQLite. Existing live schema untouched. Additive rollback leaves new tables unused.

Step12: no new schema migration. Publication service rehearsed on already migrated isolated sqe_refactor; proposed Config41/publication/audit all rolled back. Unit migration-history corruption test ran in temporary schema and rolled back; production journal untouched. Live deployment flag unchanged.

## Step15 backup and read rehearsal
Object archive: O:/CodexBackups/document-platform/objects-2026-10-22.tar.gz.7655 objects verified with stable before/after inventory and per-object SHA256. Archive SHA25609e18e95aea8c9dc1910070b8652d7573fe70f82a14f44cc205682a7573b3d5c. Approximately841 MB, outside Git. No live objects modified. This capture and the earlier PostgreSQL baseline differ in time; final cutover requires a fresh coordinated snapshot.
Read-only PostgreSQL check:40 revisions,67 case pins,0 mismatches using normalized repository reads. Publication rehearsal: proposed41, exact round trip, rollback, original rows unchanged. Docker client exit stalled after these aggregate success messages; no data corruption or runtime activation inferred. Docker recovery is tracked in CHECKPOINT.
