# Configuration storage — first implementation slice

`store.py` introduces separate publication and entry tables. It does not modify
the live Config model, startup, API, extraction, or case pins. The first migration
has been rehearsed only on the isolated restored database. Schema-specific entity tables and typed business policies remain
future work; this lossless layer is their compatibility foundation.

The caller owns transactions. Imports are organization/revision scoped and
idempotent, reject changed content for an existing revision, and verify a
deterministic digest on reconstruction. Unknown top-level properties remain in
extensions. Do not treat this API-level protection as database-enforced
immutability: database constraints/triggers and publication authorization are
required before runtime activation.

Tests use isolated SQLite and synthetic values, plus application default payload
round trips. All 40 restored historical configurations also passed PostgreSQL
import and reconstruction. Next gate: typed section contracts and configurable
identity bindings, followed by read-only shadow evaluation.

## Explicit schema migration

Set `REFACTOR_DATABASE_URL` through the process environment. Run:

```text
python -m app.configuration.migrate --expected-database sqe_refactor
```

The command requires the actual database name to match the explicit target,
serializes migration execution, checks applied file checksums and runs DDL plus
the journal update in one transaction. It is never called by application startup.
Migration checksums normalize line endings across Windows and Linux.

The isolated rehearsal uses `app.configuration.verify_postgres` with the same
target argument. It imports history twice and fingerprints original configuration
and case rows before/after. No report or extraction is activated.

Rollback at this additive stage means retaining the old application and leaving
the unused new tables in place. No destructive downgrade command is provided.
The SQL statement splitter supports ordinary DDL only; introduce a suitable
migration tool before procedural SQL or more complex dependencies are required.

Migration 0002 adds dedicated identity policy/binding tables. New imports validate
identity paths before writing. Compatibility reconstruction preserves explicit
empty bindings and detects tampering through the publication digest. The read-only
shadow command verified 67 restored cases with no changes in findings. Dedicated
UI editing, remaining business-policy tables and activation are still pending.
