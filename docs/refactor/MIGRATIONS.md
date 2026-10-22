# Migration ledger

No live migrations executed. No refactor configuration activated.
Baseline database dump initiated; storage backup and restore rehearsal pending.
All future entries require migration identifier, source/target version, environment, status and rollback procedure.
`nBaseline restore rehearsal complete in disposable isolated PostgreSQL. No application migration executed. Restored container retained stopped.

Step 2: 0001_publications applied to sqe_refactor in stopped-after-test sqe-refactor-baseline-db only. Replay applied zero migrations. Journal checksum recorded. 40 publications imported twice without replacing originals or case pins. No live migration. Rollback: old application remains authoritative; additive tables can remain unused. No destructive downgrade.

Step 4: 0002_identity_bindings applied on sqe_refactor only. Migration replay empty. Configuration history and case rows verified unchanged; no new live tables. Restored DB retained stopped. Additive rollback remains old runtime plus unused tables.
