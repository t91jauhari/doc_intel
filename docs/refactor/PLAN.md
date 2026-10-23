# Refactor plan and current position

Current position: **Step40 explicit family catalog verified, including custom-only end-to-end processing. Backend regression, engine199+81subtests and clean-export126 passed. GitHub authentication and preview web launch await user action.**

No live cutover. Status refers to isolated implementation, not activation.

| Point | Status | Completed | Remaining |
|---|---|---|---|
| B0 Baseline and isolation | Complete in isolation | Git/database baseline and restore; verified 7655-object backup | Coordinated cutover backup under C1 |
| B1 Inventory and regression | Partial | Initial inventory, saved history, baseline failure recorded | Complete all business configuration locations |
| D1 Configuration schema | Partial | Publications, entries, identity bindings, family-rule membership; 6 migrations; PostgreSQL immutability and context rows | Remaining entities |
| D2 Typed contracts/compiler | Partial | Lossless history, identity/text comparison contracts | Full configuration typing and policy types |
| M1 Import/publication | Complete in isolation | 40 imports; atomic writers; explicit initialization; verified/normalized reads; 67 pins checked | Activation tracked under C1 |
| R1 Grouping and SOP | Partial | Identity, comparisons, applicability, context registry; custom profiles and editors | Complex/visual policy contracts; explicit catalog browser acceptance |
| R2 Services/providers | Partial | Configuration/provider routers and services; extraction adapters; report read models | Remaining API services and provider internals; final browser acceptance |
| R3 Datasets/reports | Complete in isolation | Dataset registry, family report mappings and comparison policies;67cases/3028fields parity | Browser acceptance/activation under V1/C1 |
| V1 Final verification | Partial | Sharded backend coverage, PG/Temporal integration, frontend build;54cases/7049findings | Current UI browser acceptance, field-policy migration/native acceptance |
| C1 Cutover/rollback | Prepared, not activated | Production compose and coordinated rollout/rollback runbook | Target-specific rehearsal, coordinated capture and activation |

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
