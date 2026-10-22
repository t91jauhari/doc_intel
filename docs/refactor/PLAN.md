# Refactor plan and current position

Current position: **M1 completed in isolation (Step 15); Step23 provider connectors verified; Step24 dataset registry verified; Step25 report bindings verified; remaining native validation/SOP contracts next**.

No live cutover. Status refers to isolated implementation, not activation.

| Point | Status | Completed | Remaining |
|---|---|---|---|
| B0 Baseline and isolation | Partial | Git/database baseline and restore; verified 7655-object backup | Coordinated cutover backup under C1 |
| B1 Inventory and regression | Partial | Initial inventory, saved history, baseline failure recorded | Complete all business configuration locations |
| D1 Configuration schema | Partial | Publications, entries, identity bindings, family-rule membership; 6 migrations; PostgreSQL immutability and context rows | Remaining entities |
| D2 Typed contracts/compiler | Partial | Lossless history, identity/text comparison contracts | Full configuration typing and policy types |
| M1 Import/publication | Complete in isolation | 40 imports; atomic writers; explicit initialization; verified/normalized reads; 67 pins checked | Activation tracked under C1 |
| R1 Grouping and SOP | Partial | Identity, comparisons, applicability, context registry; custom profiles and editors | Complex/visual policies; reserved native compatibility catalog |
| R2 Services/providers | Partial | Preview/publication; extraction service and adapters | Remaining API services and provider internals; final browser acceptance |
| R3 Datasets/reports | Partial | Immutable dataset registry, explicit import, 67 saved-case parity checks | Comparison policy configuration and remaining report presentation defaults |
| V1 Final verification | Partial | Unit/API/browser checks, 54 cases/7049 findings | Full suite, extraction/dataset acceptance, native validation outcome issue |
| C1 Cutover/rollback | Pending | Original app unchanged | Backups, activation, monitoring and rollback |

CHANGES.md records files and commits; VERIFICATION.md records checks;
MIGRATIONS.md records isolated schema changes; CHECKPOINT.md records resume state.
Do not equate implemented, tested, migrated and activated.

## Step 12 rollout boundary

CONFIGURATION_STORAGE_MODE defaults to legacy. Explicit dual mode requires all
configuration tables and matching PostgreSQL migration checksums; no startup
schema creation. Interactive publishing writes legacy Config, normalized rows
and audit in one caller-owned transaction. Case pins/extraction stay unchanged.
All writers use the persistence boundary. Verified/normalized reads are implemented
and tested; activation requires dual mode and full historical imports.
