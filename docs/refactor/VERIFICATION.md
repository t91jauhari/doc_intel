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

Step 8: 45 focused tests passed in 7.14s. Draft generation CLI converted 2 selected v40 rules (AO_SYSTEM_7/13) to private file, activated=false. Full-case shadow: cases_checked36, ordered_findings5623, conversions144 (occurrences across versions, not unique rules), mismatches0. Blocked18 on sop_review_bypass validation, unsupported/no-conversion cases13. Compared ordered rule IDs/status/eligibility/category, point summaries and category scores using saved case contexts. Message wording and entire evidence payload equality are not claimed. Live health ok; isolated database stopped. Initial unit-test fixture used an incorrect padded rule ID and was corrected to select a supported packaged rule.

Step 9 evidence: API/runtime/upgrade selection 19 passed (42.95s), including admin restriction, stale-version rejection, invalid selections and no Config row/payload changes after preview. TypeScript passed after final changes. Fresh local preview browser login/selection/preview/apply-to-draft/normalization edit verified; v7 remained published. Family filtering issue found during smoke and corrected. Controls visually inspected and checkbox layout corrected. Preview invalidation covers family/draft/version changes. Screenshot outside Git in outputs/refactor-step9. No production build claimed; Next dev routes compiled. Preview processes stopped and live API healthy. No live writes/model calls.

Step 10: 13 compatibility unit tests passed (2.19s); earlier API/upgrade/compatibility selection16 passed (34.95s), overlapping. Checked missing-only behavior, source immutability, administrator overwrite rejection, stale version, role restriction, no DB publication, grouping/profile equality, strict bools. Full saved-context rehearsal --compatibility: cases54, ordered findings7049, conversion occurrences216, mismatches0, blocked0, compatibility cases18. Other13 cases have no supported match conversion. Bypass disabled and no model/extraction runs. Live API health ok, restored DB stopped. No production migration.

Step11: initial29 focused passed. After visual-region guard final43 focused passed (5.54s);5 API tests passed (36.81s); TypeScript final passed. API tests cover version, family scoping, role restrictions, unchanged config. Pure tests custom schema/wrapped text/numeric-array exclusion/self comparison/visual rejection. Browser rebinding + applicability + read-only Test settings successful on synthetic DB with0 docs; v7 remained published. Signature evidence originally surfaced as text during smoke: excluded by presence-region structure and rejected in generic validator. Screenshot outputs/refactor-step11. Preview API restart produced temporary dashboard disconnect during testing; recovered. Both servers stopped. Live health ok. Nonstandard NODE_ENV warning in test host remains; no production build claimed.

Step12 evidence:17 publication/API/transaction-flow tests passed,5 PostgreSQL migration tests passed,1 final source-immutability/instruction-compilation test passed separately. Tested dual equality, stale409, missing-schema503, legacy-mode compatibility, failure before/after normalized insert rollback, unchanged audit counts and case pin. PostgreSQL checksum mismatch rejected in temporary schema. verify_publication ran twice; final includes audit count check: proposed41, round_trip_equal=true, rolled_back=true, original_rows_unchanged=true, activated=false. Source tables/publication/audit preserved. Live API healthy; isolated DB stopped. Full suite/cutover not claimed.

## Step 13
New writer/startup/dual-guidance suite: 4 passed (35.89s). Broader publication/guidance/account regression: 26 passed, 1 failed (179.54s). Failure was a fixture with 29995 raw prompt characters exceeding 30000 after mandatory spatial instruction compilation. Corrected fixture budgets compiled length; Docker rerun blocked by exhausted C: and unresponsive Docker control. Backend AST parse passed. No final green-suite claim. Live API remained healthy. See CHECKPOINT storage incident for recovery.

Step14 offline backup verification: 3 unittest tests passed in0.042s; backend AST parse passed. Docker inventory timeout confirmed after8s. No live backup/restore success claimed.

## Step15
Fresh repository/publication/writer/guidance suite:22 passed (174.16s), including corrected compiled prompt-length fixture. Broad account-opening/field-reprocessing/platform regression:52 passed (407.24s).40 PostgreSQL revisions and67 pins read normalized with0 mismatch in a read-only transaction. PostgreSQL publication rehearsal proposed41, exact reconstruction and rollback, original rows unchanged. Earlier6 failures from a running process mixing pre-edit Settings with new modules were discarded; no compatibility fallback was added to hide them. Source must remain frozen during checks.
Object backup verified7655 objects. Automatic cleanup denied recursive deletion of old94 MB preview cache on O:; left untouched. Test containers use --rm. No image rebuild or broad prune.

Step16:6 PostgreSQL migration tests passed (0.98s). Initial parameter handling failed on PostgreSQL format placeholders; corrected by explicit no_parameters execution and reran successfully. Migration0004 isolated restore: replay0 changes,40 revisions checked, source rows unchanged. Post-trigger publication rehearsal exact and rolled back, source rows unchanged. No live schema activation.

Step17: grouping and legacy refresh17 passed (59.83s). Strengthened2 legacy snapshot-idempotency tests passed (13.46s). Both READY and missing-document FAIL paths preserve pinned payload and avoid duplicate report artifacts. Actual identical-content upload dedup is covered independently from distinct fixture PDFs. Earlier baseline grouping failure is resolved as an outdated assertion, with dedup coverage retained.

Step18:39 focused tests passed60.27s;43 automation/Forex/encoding tests passed117.31s;6 PostgreSQL tests passed1.08s. Final strengthened registry/migration/runtime24 passed17.99s. TypeScript passed. Browser unpublished choice-list edit validated,0 documents, version7 unchanged.40 PostgreSQL history revisions unchanged after0005, replay0; proposed41 rollback equal. Preview stopped and generated cache removed.

Step19:initial3 custom contract/pipeline tests passed11.92s;20 custom/guidance/reprocessing passed220.83s; final5 custom tests12.52s;10 existing schema/reusable-profile/variant tests44.12s. Extended custom pipeline including selected field reprocessing and saved profile guidance passed24.18s. TypeScript passed. Browser draft creation validated at publishedv7,0 documents; no publish/extraction outcome implied by browser. No live provider calls.

Step20: TypeScript passed. Browser validated new comparison definition and explicit flow membership, with1 selected check; no publish. No backend tests added for this reversible UI-only change; existing server validation and comparison runtime remain unchanged.0 preview documents means no extraction-result coverage from this browser run.

Step21:47 provider/service/Spider recovery/config-store tests passed204.05s;3 mocked Llama classification/parse-reuse/uncertain-submission tests passed33.77s. Unsupported provider fails before dispatch, copied configuration cannot mutate source, classification-only result and exception identity retained. Hash persistence compatibility tests passed through store re-export. No cloud calls.

Step22:10 repository/custom-profile tests23.70s, including PostgreSQL row-lock concurrency and committed receipt preservation.8 provider recovery/native reuse tests82.67s. TypeScript passed. Failure serialization rolls back status/state; later processing rollback cannot remove committed checkpoint; nested state does not leak. Temporary provider_state_contract_tests schema dropped and verified absent.

Step23:48 connector/Spider/prompt-delivery/selected-field tests passed373.81s; TypeScript noEmit passed. Restored PostgreSQL2 connector option records accepted; no credential reads. Mock/fixture providers only. Advanced connector browser controls await final UI acceptance.

Step24:22 dataset contract/API/comparison/PostgreSQL migration tests passed17.73s. TypeScript passed.40 configuration revisions round-trip unchanged;0006 replay idempotent.2 immutable dataset imports.67 read-only saved-case comparisons equal between bundled and registry. Browser advanced connector limit persisted across reload then restored; catalog selector populated from API. Previewv7 unchanged/0 documents; no model calls. Next temporary cache removed via scoped git clean after dry-run.

Step25:14 report baseline tests passed30.09s. Extended suite31 passed/1 fixture mismatch due Python tuples vs JSON arrays; corrected fixture to actual persistence contract. Final25 report/configuration storage tests passed8.96s; TypeScript passed.449 saved report rows equal to previous implementation; read-only transaction. Browser report mapping draft validated0 docs, discarded, publishedv7 unchanged. Preview/cache cleaned.

Step26:32 field/Spider tests passed141.33s;39 field/custom/reread tests passed156.95s;69 field/workbook/Forex/account tests passed100.26s; final25 field tests passed3.53s. Overlapping counts are not unique totals. Direct configured-field SOP integration confirmsPASS1/FAIL0; existing errors preserved. TypeScript passed. Browser NIK16 draft validated0 documents; discarded/publishedv7 unchanged. No paid calls/live mutation; cache/test helpers cleaned.

Step27:30 account policy/runtime tests passed66.29s;45 official/SOP/scoring/generic tests passed41.94s; TypeScript passed.6180 policy JSONs across40 historical revisions pass strict contract unchanged. First explicit-condition shadow36 cases/5623 findings/108 proposedconversions0 score/state differences;18 older configs blocked pending compatibility rehearsal. Full503 suite underway; no full result recorded yet.

Step28:4 exporter stdlib contract tests passed. Audit284 selectedfiles2.22MB192excluded0blockers, no output written. Full backend segment177 passed7PG skipped before outdated family closed-dataset assertion; fixture updated for registry semantics.20 affected family/dataset tests passed51.32s; tests explicitly assert unregistered publication rejected/unchanged version and registered custom reference accepted. Remaining suite session98361 running. Final conditional compatibility shadow54 cases7049findings162proposals18compat0mismatches0blocked, read-only.

Step29:40 enum/Spider/field tests passed12.37s;7 real PostgreSQL migration tests passed1.24s. Previous-head clean export76 synthetic tests passed35.15s. Frontend optimized production build passed compilation/TypeScript/page generation. Auto-review rejected production-preview start with no detailed reason (blocked by policy); do not claim production browser smoke. Broader frozen backend remainder session7895 still running.

Step30:26 report/family/latest tests passed67.22s; TypeScript passed.19 settings/report/writer/enum tests passed60.34s. Settings subprocess forbids every Path.mkdir during import; explicit SQLite initializer succeeds with missing nested parent. Corrected native retry fixture passes14.10s. Broad segment163 passed before fixture mismatch; remaining tail pending. Standalone build trace folder136KB inside checkout/no links removed with scoped Git cleanup after path verification/dry-run.

Step31:11 dataset registry/API/private JSON import tests passed30.62s. Parse file errors return generic contract failure without source values. Full remaining tail session39864 still running; all test counts remain overlapping until consolidated.


## Step 32 — Remove Llama application provider
User requested removal of Llama, superseding the Step 31 custom-profile Llama support gap. Removed its adapter, paid execution implementation, connector settings form, and unused parser tier/version controls. New configuration publication accepts Spider-AI or development fixtures only. Historical Llama configurations remain readable; extraction and selected-field reprocessing fail explicitly before submission and require an explicit case upgrade. Legacy connector routes return HTTP 410, without deleting stored credentials or historical receipts. Native deterministic validation remains available. Standalone engine compatibility and historical SDK error decoding are not application provider integrations.

Files: backend/app/{domain,main,provider,field_reprocessing}.py; backend/app/extraction/{adapters,service,connector_repository}.py; frontend/app/settings/page.tsx; frontend/components/spider-connector.tsx; backend/tests/test_extraction_service.py; docs/refactor/{CHECKPOINT,CHANGES,VERIFICATION}.md.

Verification: 14 focused extraction/removal tests passed; frontend TypeScript check passed; git diff --check passed. Original live stack unchanged; this change is implemented in the isolated refactor only, not deployed. Earlier broad backend tail run was stopped on this owned test runner when scope changed; old Llama integration tests require retirement/replacement before a full-suite acceptance claim. Broader refactor phases remain pending. No provider calls, data migrations, paid jobs, or public pushes performed.


## Step 33 — Provider removal regression cleanup
Removed obsolete Llama paid integration tests; retained the standalone engine and historical error decoding tests. Native deterministic validator unit cases now explicitly select development fixtures; custom-profile tests select Spider. Connector encryption/access tests exercise Spider. Upload/dashboard labels now describe the supported provider accurately; historical case labels remain visible. Corrected a non-UTF-8 settings label and made public export reject invalid source encoding with a clear diagnostic.
Files: backend/tests/{test_connector_contracts,test_custom_profiles,test_enum_display,test_field_reprocessing,test_parse_evidence,test_platform,test_prompt_delivery,test_schema_descriptions}.py; frontend/app/{page,settings/page,upload/page,cases/[id]/page}.tsx; scripts/{export_public_source,test_export_public_source}.py; docs/refactor/{CHECKPOINT,CHANGES,VERIFICATION}.md.
Verification: initial full run 130 passed/7 PG skipped before obsolete connector expectation; 5 exporter tests and frontend type check passed. Three isolated backend shards are running (sessions64280,44135,41827); shard2 restarted at custom profiles after provider selection correction (42 earlier passes). Runtime source frozen until they finish. New comparison policy module/manifest/editor are unintegrated work in progress, not active or accepted. No live changes.


## Step 34 — Configurable reference comparison and application services
Family comparison_policy now controls conservative text comparison enablement, review/acceptance similarity, length/edit limits, and field/suffix exclusions. Release defaults captured in config_data/dataset_comparison_v1.json. Typed validation rejects unused/invalid options; changed numeric tokens still prevent fuzzy matches. API comparison resolves the case-pinned family policy and includes policy in the comparison fingerprint/result. Family configuration has an editor using server defaults. No extraction values or SOP scores are rewritten.
Configuration replay moved from API into configuration/replay.py with caller-owned read session. Latest report selection moved into ReportQueries/ReportAudience, preserving access filtering before ranking and eliminating one case lookup per report.
Files: backend/app/{dataset_comparison,domain,main,report_queries}.py; backend/app/configuration/{dataset_policy,replay}.py; backend/app/config_data/dataset_comparison_v1.json; backend/tests/{test_dataset_policy,test_platform,test_storage}.py; frontend/components/{dataset-policy,document-families}.tsx; frontend/lib/types.ts; docs/refactor/{CHECKPOINT,CHANGES,VERIFICATION}.md.
Verification: sharded baseline covered all507 backend tests after retiring removed Llama tests; PostgreSQL-only cases separately passed (11 checks, including8 previously skipped), Temporal2 passed on ephemeral test service. Shards173passed/7skipped;190passed before stale storage expectation plus corrected21tail (4 repeated);42 before custom provider correction plus75resumed/1skipped plus2Temporal. Fixed storage expected-byte assertion using shared uploaded_pdf helper; no storage implementation defect. New comparison/report/replay affected selections27+5 passed; TypeScript passed. Read-only old-vs-new comparison on67restoredcases/3028fields:0differences,0writes. All11 new policy checks passed, including publication and pinned-case isolation. Current backend collection518tests; baseline507 covered plus11 new checks. UI browser acceptance still outstanding after earlier automatic preview launch rejection. R1/R2/D1/D2/C1 broader remaining work is not complete. No live activation.


## Step35 — Configuration boundary and production release preparation
ConfigurationEnvelope validates root shapes and finite JSON before profile/policy processing, retaining unknown extensions without adding defaults to the stored payload. Configuration read/publication/replay/catalog/workbook HTTP endpoints moved from main.py to configuration/api.py; application publication/replay services and request/response contracts are retained. Root provider ID validation remains application-owned; historical configurations remain readable.
Files: backend/app/configuration/{contracts,api}.py; backend/app/{domain,main}.py; backend/tests/test_configuration_contracts.py; backend/tests/test_dataset_policy.py (synthetic standalone upload helper); docs/refactor/{CHECKPOINT,CHANGES,VERIFICATION,PLAN,INVENTORY.csv}.
Verification:30 root/custom-profile/writer/comparison checks passed;40 historical revisions passed structural validation with0 payload changes. Current interface production build passed using documented --webpack mode; default Turbopack rejected the intentionally shared dependency junction. TypeScript/static page generation passed. No preview server started. Generated .next and isolated tracing artifacts removed after resolving paths inside this checkout. All16 configuration-router regressions passed; no claim of final browser acceptance.
Release preparation: compose.production.yaml requires externally supplied image references/DB/object storage/Temporal/secrets, secure cookies/TLS, separate deployment name/queue, readonly runtimes and loopback frontend binding. docs/refactor/ROLLOUT.md records coordinated capture, import/verification gates, rollout and receipt-aware rollback. Compose schema validation and5 export-guard tests passed. These are prepared files, not an activated release. Public exporter includes only the deployment runbook among refactor records. All live code/data remain unchanged.


## Step36 — Captured native catalog instead of Python business literals
Moved native profile labels/classification descriptions/filename aliases, grouping prefixes/messages, family defaults, Forex vocabulary/checkpoint labels and historical rule patches into config_data/native_catalog_v1.json. Existing publications still supply their saved profile/grouping/policy settings; this release data is for seeding and explicit historical compatibility, never an automatic publication. The two historical policy_review conversions now use declarative when/set data rather than rule-ID branches in Python. Concrete configured operators remain unchanged.
Files: backend/app/{domain,document_families,forex_sop}.py; backend/app/configuration/native_catalog.py; backend/app/config_data/native_catalog_v1.json; docs/refactor/{CHECKPOINT,CHANGES,VERIFICATION}.md.
Verification: exact default_config fingerprint parity; family catalog equality;43 legacy rule projections equal before/after,0 differences and0writes. Forex27 tests passed. All28 grouping/Windows-encoding/family checks passed. This externalizes seed/compatibility data; it does not remove the native engine adapter requirement or finish all remaining service boundaries. No live changes or provider calls.


## Step37 — Provider settings application boundary
Connector administration now uses extraction/administration.py inside caller-owned transactions. extraction/api.py owns authenticated settings routes and removed-provider410 routes. Main composes routers instead of managing credentials. Known advanced settings, legacy private options, encryption and audit behavior remain preserved. Removed unused Llama options DTOs and prompt builders; standalone engine and historical SDK error decoding remain available without registering Llama extraction.
Files: backend/app/extraction/{administration,api,connector_contracts,connector_repository}.py; backend/app/{main,extraction_prompts}.py; docs/refactor/{CHECKPOINT,CHANGES,VERIFICATION}.md.
Verification: All31 connector/service/prompt checks passed. No provider calls or live writes. Public remote inspected read-only and has no refs; refresh sanitized source before considering any public publication. Never push this private history.


## Step38 — Public snapshot privacy and standalone engine acceptance
Sanitized customer-specific sample filenames/comments/docs and upload examples with generic customer placeholders. Native default policy stamp references now instruct administrators to configure an authorized reference; existing DB revisions/pins are untouched. Export guard now rejects private Google document links as well as invalid UTF-8/credential shapes, rather than publishing document identifiers. Generated public README states the refactor is still in progress.
Files: backend/app/domain.py (comment only); frontend/app/upload/page.tsx (example labels); engine/profiles.py (legacy CLI example paths); engine/{README,ektp/README,invoice/README,lld/README,riplay/README,valas1/README,valas2/README}.md; engine/{ektp,riplay}/policy.json (reference metadata only); engine/tests/test_ektp.py; scripts/{export_public_source,test_export_public_source}.py; docs/refactor/{CHECKPOINT,CHANGES,VERIFICATION}.md.
Verification: clean source candidate from Step37 has304files/2.25MB/0 scanner blockers and126 included synthetic tests passed without customer fixtures. Subsequent privacy changes require fresh export. All199 engine tests plus81 subtests passed. Engine test failure was an outdated expectation: approved enum aliases pass; missing enum values FAIL; unsupported enum text requires review and configured raw fallback is retained. Only tests were aligned; validator behavior did not change. Six export-guard tests passed. No public push yet; never push the private history.


## Step39 — Clean GitHub snapshot awaiting authentication
Fresh public export: work/refactor/public-source-candidate-step38, source54e0af3,304files/2.25MB,305staged including manifest,0 private reference rows.126 synthetic tests passed on the fresh export; every file hash/size verified. Created independent main commit9a685d4 (human Git identity/message), with no original history. git push --set-upstream origin main is waiting in Git Credential Manager (exec61612, credential-manager PID18372); no remote success/refs confirmed. User authentication requested asynchronously. Do not push from the private source checkout, force-push, or claim publication completed. Future accepted source changes need a new sanitized export/update to this clean history.

## Step40 — Explicit family catalogs and workbook prompt repair
family_catalog_mode=explicit allows a catalog containing only configured families/profiles. Absent mode retains exact legacy starter behavior. Removed mandatory native profile guard only for explicit mode; field/schema/context/rule bindings remain validated. UI family list and selection honor explicit mode; the settings switch materializes the current list safely. Workbook round trips preserve optional mode. Custom-only upload/extraction/SOP/report/selected-field retry works with no native profiles.
Found/fixed real workbook defect: profiles using the default system instruction exported an empty cell that failed reimport. Export now writes the effective instruction actually used by extraction. Both legacy and custom-only round trips prove instruction parity; no published configuration is changed by export.
Files: backend/app/{domain,document_families,config_workbook}.py; backend/app/configuration/contracts.py; backend/tests/test_custom_profiles.py; frontend/{lib/types,lib/document-family,components/document-families,app/settings/page}.tsx/ts; frontend/tests/document-family.cjs; work/refactor/start-preview.ps1 (local operation helper, outside repository); docs/refactor/{CHECKPOINT,CHANGES,VERIFICATION,PLAN}.
Verification:30 custom-profile/family/automation checks passed, including full custom-only pipeline and selected-field guidance persistence; TypeScript and frontend family assertions passed. No paid calls or live changes. Synthetic isolated API restarted and healthy on8100; web3100 remains unstarted after earlier automatic approval rejection. User asked asynchronously to run the supplied preview launcher. Preview v7/zero-document baseline must remain unpublished during browser checks. Remaining complex/visual policies, API boundaries and final activation are still not complete.

## Publication and preview recovery — 2026-10-23
The connected GitHub account confirmed repository ownership/write access. Published the previously verified sanitized Step38 snapshot (304 source files plus manifest) through GitHub tree/commit APIs. Remote main verified independently with git ls-remote: d22e168eaf9e7bbc66e5c6447c4dfb58886014a9. No private history or customer artifacts published. Earlier credential-manager push was stopped after verifying its owned process chain; no authentication workaround or credential export was used.
Isolated web preview is running on 127.0.0.1:3100 (webpack development mode), connected to synthetic API8100, published v7 and zero documents. Renewed user authorization permitted automatic launch; no manual startup remains required. Browser verified family catalog switch, comparison settings controls and read-only draft test with zero document replay. Draft must be discarded after remaining acceptance checks. Step41 API split remains uncommitted and full backend regression is running (exec3771); do not publish this unverified split yet.
Files changed this step: backend/tests/test_configuration_publication.py (patch moved configuration router settings rather than old main module); docs/refactor/{CHECKPOINT,CHANGES,VERIFICATION,PLAN}.md. API module inventory will be recorded after regression acceptance.

## Step41 — API feature boundaries (verification in progress)
Moved the remaining 55 route handlers and 19 request models out of the application entry point. main.py now contains lifecycle, middleware, health and router composition. Endpoint bodies, transaction boundaries and authorization checks are preserved. OpenAPI parity verified all65paths and their methods/parameters/status/request/response contracts; only tags and one internal PreviewInput schema namespace changed. Some feature routers still perform direct database orchestration; service separation remains explicitly tracked rather than claimed complete.
Created: backend/app/api/{__init__,dependencies,contracts,views,authentication,administration,intake,documents,operations,cases,comparisons,evidence,field_processing,notifications,reports,exports}.py and backend/app/api/README.md.
Changed: backend/app/main.py; backend/tests/test_configuration_publication.py; docs/refactor/{CHECKPOINT,CHANGES,VERIFICATION,PLAN,INVENTORY.csv}.
Browser acceptance: explicit family catalog switch; family comparison editor and read-only test; conditional EDD source/values editor; Spider/development-only provider choices; draft discarded; restart against extracted API routers successful. Synthetic state verified directly: published7,0documents. TypeScript check passed. Full backend suite exec3771 and Temporal exec34714 still running; no Step41 commit/public export until accepted.
Public repository main remains verified Step38 snapshot d22e168. API8100 and web3100 run isolated code; original8000/3000 remain unchanged.

Step41 verification continuation: the initial ordered backend run was deliberately interrupted after276passed/7PostgreSQLskipped (905.02s), then collection confirmed526non-Temporal nodes. Remaining nodes[283:] (243 nodes) resumed as three81-node shards, sessions69213/16173/47561. Each runner prefixes collected relative paths with /refactor/backend/tests; an initial path-only launcher attempt ran zero tests and was corrected before resuming. This partitions the remaining work without dropping the interrupted test. Temporal2passed49.40s (session34714 complete). PostgreSQL migration/provider-state11passed2.91s (session78070 complete), covering all8database-dependent checks separately. TypeScript passed. Preview state remains7/0 and liveAPIhealthy. No Step41 commit yet.

## Step41 accepted — 2026-10-23
All528 backend tests covered successfully: initial276passed/7PGskipped; remaining shards81passed,71passed before stale workbook expectation, corrected tail10passed,80passed/1PGskipped; Temporal2passed; PostgreSQL11passed covers all8skips (3 additional checks repeat previously passing tests). Unique total:518non-Temporal withoutPG +2Temporal +8PG =528. No outstanding test failures. PostgreSQL tests use dedicated disposable schemas on the isolated restore. Only a Starlette test-client deprecation warning remains. Engine unchanged since its199tests+81subtests acceptance. TypeScript passed; browser acceptance and65path OpenAPI parity passed.
Step41 is implemented and tested in isolation. Remaining command-service separation, complex/visual policies, native field-policy acceptance and coordinated cutover are still tracked as incomplete. This is not a live activation or a complete architecture claim. Generated frontend/next-env.d.ts changes belong to the active development preview and are excluded from the commit.
Next: fresh sanitized export from the accepted commit, verify manifest/source guards and included synthetic tests, then update public main with an expected-head lease. Never push private Git history.

## Step41 publication complete — 2026-10-23
Accepted private implementation commit:a469dd8. Fresh sanitized candidate:work/refactor/public-source-candidate-step41,321sourcefiles/2,263,135bytes plus manifest. Source guards:0blockers; all321hashes/sizes verified;6export-guard tests passed;126included synthetic tests passed111.10s. Public main independently verified11520ede47b0025d10232d3eead01819e7d887ee (parentd22e168) through git ls-remote after an expected-head, non-force connector update. No private history, credentials or customer artifacts published.
All test containers removed themselves. Original API8000 and isolated API8100 healthy. Web3100 remains running (exec89237) with active development cache; browser tab10 shows configuration. Published synthetic state7/0 preserved. Only generated frontend/next-env.d.ts remains outside commits while preview is active.
Cleanup attempt for obsolete public-source-candidate, public-source-candidate-step37 and public-source-candidate-step38 was rejected by automatic approval review: blocked by policy. Those small copies remain; no alternate deletion or bypass attempted. Backups and the previously blocked preview cache remain retained. Do not retry rejected cleanup without new authorization.
Remaining refactor work: command-service separation beyond feature routers; complex/visual SOP contract generalization; remaining configuration entity/field-policy acceptance; final target-specific coordinated cutover and rollback. Current unit is complete, whole refactor is not declared complete. Resume from PLAN.md with the current source/publication facts rather than earlier authentication or manual-preview blockers.


## Step42 accepted locally — 2026-10-23
554 unique backend tests covered: shard0 143passed/1PGskip; shard2
216passed/7PGskips; shard1 102passed before runner correction plus83passed
in corrected tail. The8 PostgreSQL-dependent skips passed in PG integration
(11passed including3 overlap checks); Temporal2passed. Unique coverage:
544 non-Temporal/non-PG +8PG +2Temporal =554. Historical review-policy text
compatibility is fixed and its regression passes. One remaining warning is the
upstream Starlette/httpx test-client deprecation, not a runtime failure.

Engine199tests+81subtests passed. API parity65paths; source-verified saved-case
replay67cases/7608findings/0differences/0blocked; defaults equal; source rows
unchanged;0paid calls. Seven migrations applied/replayed only in isolated PG;
40source histories unchanged;40freshv2 imports exact. TypeScript/family assertions,
production webpack build,13static assets and authenticated production browser
configuration passed. Browser console has no error/warn entries. Synthetic
publishedv7/0documents preserved. Production web3100 session17759 and API8100
remain available; original3000/8000 stay on original code.

Local copied-database rollback to Step41 and restoration of current API passed.
New policy types require compatible workers; remote deployment/coordinated live
cutover remains outside the user-selected local-first target. No startup business
publication, case repinning, provider submission or original schema change.
All final test containers auto-removed. Retained136124-byte generated tracing
folder is locally excluded after automatic approval rejected cleanup; do not
retry deletion. Necessary backups retained. Full file list:STEP42_FILES.md.

Next publication gate: commit this accepted source; clean allowlisted export;
verify hashes/guards and included tests; expected-head public update from11520ed.


## Step42 delivery complete locally — 2026-10-23
Accepted source commit:b3116354fccedb0cc7885c92055c32ae28716e9d.
Public sanitized main:9cdc21cff658b83fad34578cc19aae8a47f16bf9,
parent11520ede47b0025d10232d3eead01819e7d887ee; expected-head update,
no force, independently verified by git ls-remote. Export354source files,
2361050bytes plus manifest; all hashes/sizes verified;0scanner blockers;
6export guards and127 included synthetic tests passed215.78s. Private history,
customer samples, credentials and browser evidence were not published.

Clean backend image:sqe-refactor-api:step42,
sha256:76ffe5a06361060266b827b729f8d4a1674cb1f82c6beebed2b2f03ba30a2825,
414499936bytes. First build hit transient package-index unavailability;
unchanged pinned versions resolved on retry. Fresh build succeeded; packaged
API health/auth/configv7/cases and pip check passed using a copied synthetic DB,
network disabled,0provider calls. Smoke container auto-removed. No dependency
versions were changed. Production frontend build/browser and standalone3100
remain accepted. API8100/original8000 healthy; original3000 code unmodified.

All local PLAN items complete. Remote server deployment and coordinated live
cutover are outside the explicitly selected local-first target. Business
configuration lives in versioned revisions; bootstrap/legacy catalogs preserve
historical compatibility. Authentication, bounded evaluator algorithms and
workflow state transitions intentionally remain code capabilities.

Recovery: read PLAN.md, FINAL_ACCEPTANCE.md, STEP42_FILES.md and this checkpoint.
No pending test/build/publication process remains. Preview web session17759 and
API container sqe-refactor-preview-api are intentionally running. Necessary
backups and accepted image/source artifacts retained; small cleanup-blocked
folders remain excluded. Never retry rejected deletion without renewed approval.
Documentation closure changes:docs/refactor/{PLAN,INVENTORY,CHECKPOINT,CHANGES,
VERIFICATION,STEP42_FILES,FINAL_ACCEPTANCE}. No runtime change after acceptance.
