# Refactor plan and current position

Current position: **M1 - validated import and publication integration (Step 12)**.
No live cutover. Status refers to isolated implementation, not activation.

| Point | Status | Completed | Remaining |
|---|---|---|---|
| B0 Baseline and isolation | Partial | Git baseline, database backup/restore | Object-storage backup |
| B1 Inventory and regression | Partial | Initial inventory, saved history, baseline failure recorded | Complete all business configuration locations |
| D1 Configuration schema | Partial | Publications, entries, identity bindings, family-rule membership; 3 migrations | Remaining entities and database immutability |
| D2 Typed contracts/compiler | Partial | Lossless history, identity/text comparison contracts | Full configuration typing and policy types |
| **M1 Import/publication** | **Current - partial** | 40 historical imports; opt-in atomic publication | Other writers, normalized reads, rollout |
| R1 Grouping and SOP | Partial | Identity, text comparisons, applicability, editor | Complex/visual policies, dynamic profiles and contexts |
| R2 Services/providers | Partial | Preview/publication services, upgrade router | Remaining API services and provider/prompt boundaries |
| R3 Datasets/reports | Pending | Existing report compatibility retained | Dataset registry and report read models |
| V1 Final verification | Partial | Unit/API/browser checks, 54 cases/7049 findings | Full suite, extraction/dataset acceptance, baseline bugs |
| C1 Cutover/rollback | Pending | Original app unchanged | Backups, activation, monitoring and rollback |

CHANGES.md records files and commits; VERIFICATION.md records checks;
MIGRATIONS.md records isolated schema changes; CHECKPOINT.md records resume state.
Do not equate implemented, tested, migrated and activated.

## Step 12 rollout boundary

CONFIGURATION_STORAGE_MODE defaults to legacy. Explicit dual mode requires all
configuration tables and matching PostgreSQL migration checksums; no startup
schema creation. Interactive publishing writes legacy Config, normalized rows
and audit in one caller-owned transaction. Case pins/extraction stay unchanged.
Other writers (startup seeds and profile-guidance append) still need migration
before normalized storage can become authoritative application-wide.
