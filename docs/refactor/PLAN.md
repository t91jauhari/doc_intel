# Refactor plan and current position

Current position: **Step42 refactor and Step43 operational local preview complete.**
Live synthetic extraction,5crops,SOP/report,3export formats and persistent restart
passed with user-selected3.8-flash-high. Public mainc1e41c4 verified. Real complete
customer UAT and server-specific production deployment are separate next scopes.

The selected delivery target is complete and verify locally first. Original
ports3000/8000 remain on their existing code; isolated API8100/web3100 use the
refactored source. Remote production activation is outside this delivery target.

| Point | Status | Evidence / acceptance boundary |
|---|---|---|
| B0 Baseline and isolation | Complete locally | Git/database baseline and restore;7655-object backup verification; separate databases/ports/storage |
| B1 Inventory and regression | Complete locally | INVENTORY.csv; versioned business configuration; captured bootstrap/legacy catalogs; registered algorithms remain code capabilities |
| D1 Configuration schema | Complete locally | Seven migrations; v2 entity tables; immutable v1 compatibility;40 fresh v2 round trips |
| D2 Typed contracts/compiler | Complete locally | Identity/text/conditions/field checks/context/report/data policies plus visual/date/money; validated schemas and score groups |
| M1 Import/publication | Complete locally |40 history imports; atomic writers; explicit initialization; verified reads; immutable pins |
| R1 Grouping and SOP | Complete locally | Configured families, scope, conditions, visual review safeguards;67 cases/7608 findings replay with zero differences |
| R2 Services/providers | Complete locally |43 application operations; DTO/access/error/upload ports; crypto/domain ownership; provider receipts and adapter boundaries preserved |
| R3 Datasets/reports | Complete locally | Dataset registry; typed report bindings; configurable scoring groups; historical report parity |
| V1 Final verification | Complete locally | Engine199+81subtests; Temporal2; PG11; API65paths; production build/typecheck/assets; browser configuration; 554 backend tests covered with no outstanding failures |
| C1 Local rollout/rollback | Complete locally | Production standalone preview; synthetic copied-database rollback to Step41; new API restored; no paid calls |
| O1 Operational preview | Complete locally | Persistent API/worker;3.8-flash-high live synthetic extraction;5crops;SOP/report/3exports;restart retention verified |
| P1 Sanitized publication | Complete locally |354source files;0scanner blockers; hashes verified;127included tests; public Step42 main9cdc21c and Step43 mainc1e41c4 verified |

The local rollback rehearsal validates existing publications; old workers cannot
interpret new configured policy types. Preserve compatible workers for such case
pins. Remote deployment requires server settings, coordinated database/object
capture and receipt-aware cutover using ROLLOUT.md. It is not represented as a
completed production activation.

CHANGES.md and STEP42_FILES.md record changed/created files. VERIFICATION.md
records evidence; MIGRATIONS.md records schema changes; CHECKPOINT.md records the
latest resumable state. Existing configuration storage defaults remain legacy;
changing read/write modes or business versions is an explicit release action.

## Step44 — extended local acceptance

Current position: shared infrastructure migration and complete backend parity
verification. Reuse existing service instances with isolated database/bucket,
scoped credentials, Temporal namespace and queue. No original app cutover.
Full regression passed; final discovered wrapper-crop fix is under targeted
verification, followed by accepted-source image and sanitized publication.
Remote production deployment remains deferred pending server details. Full real
customer/model accuracy evaluation remains distinct from backend capability parity.

Step44 complete:559unique backend cases covered;36affected regression cases passed;
shared Temporal/MinIO live acceptance, restart, export and exact-source checks
passed. Source3a90a46; publicc1f4235 verified. Backend/local capability phase complete.
Complete live customer dataset accuracy evaluation remains a separate acceptance
scope; remote deployment is pending the user's server details.

## Step45 — full customer UAT, RIPLAY final-page exemption and explicit rule adoption

Step45 complete: all 10 Account Opening customer packages (35 documents: 34 PDFs +
Artha eKTP PNG) processed end-to-end on the isolated preview stack (`3.8-flash-high`)
with `COMPLETED` status and verified MinIO SHA256 hashes. Configurable
`exclude_final_page` RIPLAY paraf exemption and explicit schema-compatible case
configuration adoption (`POST /api/cases/{case_id}/configuration`) implemented and
verified across engine (`179` unittest cases / `200` total with subtests), backend
(`580` unique shard tests passed, `0` failures), and standalone frontend (`3100`).
All 10 customer cases adopted configuration `v9` (`exclude_final_page=True`,
reference `account-opening-20261023-1228379b`), completed `v9` SOP reports, and
verified PDF/XLSX/JSON exports, aggregate comparison workbook, branch Kertas Kerja,
and container restart retention with zero replayed model calls. Remote production
deployment remains deferred pending server details.

## Step46 — live actual stack cutover (`127.0.0.1:3000` / `127.0.0.1:8000`)

Step46 complete: live `sqe-document-platform` stack (`sqe-document-platform-api-1`
on `127.0.0.1:8000`, `sqe-document-platform-worker-1`, `sqe-document-platform-web-1`
on `127.0.0.1:3000`, backed by `sqe-document-platform-postgres-1` database `sqe`,
`sqe-document-platform-minio-1` bucket `sqe-documents`, and
`sqe-document-platform-temporal-1`) has been migrated and cut over to the verified
refactored release (`sqe-document-platform-api:latest` / `worker:latest`
`sha256:80902db5621d32ea9c0faa73500d911e02085b66c50c2b4829be6dee94e899b8` and
`sqe-document-platform-web:latest`
`sha256:47cedcd5cd8721d189ba6bbded6599c7c6b295a8815e68f80ba6447eb18d012b`).
Pre-cutover rollback images (`:rollback-pre-step46`), `.env`
(`private/phase46/live-pre-cutover.env`), and quiescent PostgreSQL archive
(`private/phase46/live-pre-cutover.dump`, SHA-256
`BE3BC0A53DE7E9B107A52C81E94A4F07A5991FCD43F2605AD4FD966D2A2182D6`) are retained.
All 7 configuration migrations, 40 historical revisions (`storage_version=2`), and
3 reference datasets were imported and verified; `CONFIGURATION_STORAGE_MODE=dual`,
`CONFIGURATION_READ_MODE=normalized`, and `DATASET_READ_MODE=registry` are active;
configuration `v41` (`exclude_final_page=True`, dataset
`account-opening-20261023-1228379b`) is published while all 67 historical case pins
remain preserved.
