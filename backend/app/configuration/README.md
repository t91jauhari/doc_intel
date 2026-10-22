# Configuration storage — first implementation slice

`store.py` introduces separate publication and entry tables. It does not modify
the live Config model, startup, API, extraction, or case pins. No migration has
been activated. Schema-specific entity tables and typed business policies remain
future work; this lossless layer is their compatibility foundation.

The caller owns transactions. Imports are organization/revision scoped and
idempotent, reject changed content for an existing revision, and verify a
deterministic digest on reconstruction. Unknown top-level properties remain in
extensions. Do not treat this API-level protection as database-enforced
immutability: database constraints/triggers and publication authorization are
required before runtime activation.

Tests use isolated SQLite and synthetic values, plus application default payload
round trips. Next gate: compare every restored historical configuration against
its compiled representation in isolated PostgreSQL, then introduce an explicit
versioned migration and typed section contracts.
