# Atomic interactive configuration publication

Plan position: M1, Step 12. Implemented/tested in isolation, not activated.

The existing publish endpoint now delegates to `configuration/publication.py`.
The application service copies and JSON-normalizes request data, compiles system
instructions, validates the draft, acquires the existing organization publication
lock, checks expected version, and writes a new Config revision plus audit.

Infrastructure rollout setting `CONFIGURATION_STORAGE_MODE`:
- `legacy` (default): existing persistence contract; new tables not required.
- `dual`: also imports the same revision into publication/entry/binding tables
  and verifies reconstruction inside the same transaction.

The HTTP caller owns commit/rollback. A failure after Config flush or after
normalized insertion rolls back all rows. Stale requests return409; absent tables
or mismatched PostgreSQL migration history return503. The service never creates
tables and never enables schema migration during startup. PostgreSQL deployment
requires the explicit migrations already rehearsed; SQLite metadata creation is
used only in isolated unit tests.

Historical versions, case pins, extraction inputs, authentication and CSRF remain
unchanged. A reconstruction digest is checked before return. No automatic
reprocessing or provider call occurs during publication.

Verification: 17 publication/API/flow tests passed;5 PostgreSQL migration tests
passed; final input-immutability/prompt-compilation test passed separately.
Restored PostgreSQL rehearsal proposed version41, verified equal reconstruction,
then rolled back. Configuration/case/publication/audit records remained unchanged.

## Remaining M1 work

Only interactive `/api/config/publish` uses this service today. Startup seeds,
profile-guidance append and other direct Config writers still need integration.
Normalized read authority and database-enforced immutability are also pending.
Do not turn dual storage into the application-wide source of truth yet. The live
environment has not been changed; rollout flag remains at its legacy default.

## Every writer and explicit initialization
All existing Config inserts now call persist_revision, including guidance, legacy upgrades and initial bootstrap. Revision ordering, optional normalized writes and integrity verification share the caller transaction. Legacy upgrade-specific validation is retained. API and worker startup no longer publish configuration or initialize development users.

For a new development environment, run `python -m app.configuration.initialize --expected-database <database-name-or-SQLite-path>` explicitly before starting services. APP_ENV must be development; DEV_PASSWORD must be supplied through the existing secure environment. Dual mode requires explicit schema migrations first. Initializer upgrades are separate transactions and can be safely resumed using existing release markers; initialization is not one atomic multi-release transaction. Production provisioning still requires a separate workflow.

## Pinned read rollout
`CONFIGURATION_READ_MODE` supports legacy (default), verify and normalized. Verified modes require dual writes and a completed historical import. All case-processing, extraction, grouping-repair, dataset comparison, review and API configuration lookups resolve the original configuration ID through the repository. Returned snapshots do not expose mutable ORM payloads.
Verify compiles normalized storage and checks exact parity while returning a copied legacy payload. Normalized returns the compiled payload after that same integrity check. Missing publications, wrong source IDs and differing payloads fail closed; there is no fallback to the latest revision. No read mode is enabled automatically. Rollback to legacy reads is an infrastructure setting change; both persistence forms remain available.
