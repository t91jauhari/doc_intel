# v0.3 update

See [RELEASE_0_3.md](RELEASE_0_3.md) for current evidence/RIPLAY behavior and remaining tasks.

# SQE automation implementation · v0.2.1

This release adds the agreed document-only SOP workflow and Kertas Kerja reports to the existing FastAPI, Next.js, Temporal and MinIO platform. Source code and editable templates are included in this project.

## v0.2.1 patch

Fixed Windows charmap decoding failures by explicitly reading bundled JSON as UTF-8. Added a CP1252 regression simulation and a one-command verification gate with actual Chromium and saved artifact checks. See [AUTONOMOUS_DEVELOPMENT.md](AUTONOMOUS_DEVELOPMENT.md) for upgrade instructions and development scope.

## Start and exercise it

1. Extract the project and run `start.bat` on Windows or `bash start.sh` on Linux. Docker is needed for the default MinIO service. Compose starts Temporal; the local launcher uses the development-only database worker.
2. Sign in with organization **sqe**, email **sqe@bic.local**, password **P@ssw0rd2026**.
3. Open **Configuration → Processing defaults**. Use Fixture for a free synthetic demonstration, or save your LlamaCloud connector and use Llama. Fixture output does not describe the uploaded PDF.
4. Open **Automation** to edit supported upload limits, provider tiers, classification confidence and polling settings, plus report header metadata.
5. Open **SOP rules** to edit a rule using document and field dropdowns. Select an approved source and one of the four report categories. The reference field dropdown follows the selected document and operator type.
6. Use **Test settings** to replay stored documents and case SOP comparisons. Review the results, then **Publish settings**. Publication validates the entire draft again and rejects a stale expected version.
7. Bulk upload PDFs named `Customer Name_transaction.pdf`, `_lld.pdf`, `_invoice.pdf`, `_valas1.pdf`, `_valas2.pdf`, `_ektp.pdf` or `_riplay.pdf`. Filename customer labels can be corrected before upload. All originals and case membership are committed before any classifier starts.
8. After document extraction, the separate case SOP worker starts automatically. The case page displays run status, stage and snapshot hash, findings and scores.
9. Supply **Case context and transaction metadata** when needed, with a reason and supplied-document/page evidence. Saving queues a new SOP snapshot without a paid extraction job.
10. Download individual PDF/XLSX/JSON reports. Under **Kertas kerja**, select a branch to export its latest saved case reports as one XLSX row per case.

A published configuration applies to new cases. Existing cases keep their pinned configuration, including SOP rules. Publishing does not silently change an in-flight extraction or rewrite a previous report.

## Editable workbook

Use **Automation → Download editable XLSX template** to export the current configuration. `templates/forex-workflow-config-template.xlsx` is the initial starter example. The current export is the preferred basis for subsequent edits.

| Sheet | Editable content |
| --- | --- |
| General Settings | Provider, maker/checker, extraction version, report title and approved name directory |
| Workflow | Provider polling deadlines/read retries; supported parameter JSON; required registered actions and dependency order |
| Document Profiles | Labels, filename suffixes, parse/extract prompts and native validation policy JSON |
| SOP Rules | Approved source, category, typed fields, operator, conditions, currency companions and message |
| Case Templates | Template ID, display label and required document list |
| Report Context | Region, category, activity, inspection type and period header text |
| Field Catalog / SOP Scope | Read-only references; changing these does not register new fields or expand SOP scope |
| Lists / Read Me | Excel dropdown support and instructions |

The Excel field dropdown depends on its document cell. The UI additionally filters fields by operator type. The application schema has **no NIK/identity_number field**; an account number is never offered as its substitute.

Import produces a draft only. A workbook with any error is rejected as a whole, with sheet/row/cell details. Unknown fields, operators, source references, duplicate IDs, incompatible types, missing currency companions, bad JSON, formulas, unsupported step parameters and invalid workflow order are rejected. Imports are limited to 2 MB compressed, 20 MB expanded and 500 entries per editable sheet.

Bank administrators publish organization configuration. Branch administrators retain branch-scoped case operations and user administration; they do not publish organization rules. Officers can annotate/correct permitted case data. Reviewers can record SOP observations and release reports. Auditors are read-only. API authorization and CSRF protections apply independently of UI controls.

The ordered action registry is fixed: upload → group → classify → parse → extract → normalize/validate → case SOP → report → inbox. Required steps cannot be removed, disabled or reordered across dependencies. Presets declare supported behavior; arbitrary scripts, new backend actions, schema structure changes and a drag-and-drop screen layout designer are not part of this release. Adding a document field requires a registered engine schema/validator contract and a new configuration version. Extraction schemas and their hashes are stored in new profile configurations.

Generic case-template completeness gates stay separate from scored SOP controls; to score a document presence requirement, configure an eligible `document_required` rule.

Only provider polling deadlines/retries are editable runtime deadlines in the starter workflow; the other timeout cells are fixed preset metadata. Read retries never retry provider creation. The report format list can be edited in the workbook; JSON trace snapshots are always stored. Error policies and security/scope invariants are fixed by the registered presets rather than editable arbitrary behavior.

## Eligible SOP scope

The bundled catalog contains **29 source entries**:

- Consolidated SOP1/SOP2 Nos. **2, 4, 5, 6, 7, 9**, retaining both references.
- SOP5-RIplay Nos. **1, 2, 4, 5**.
- SOP4-Stempel Nos. **1, 3, 4, 5**.
- **All 15 SOP3 system checks**, as explicitly agreed even though SOP3 has no YES column.

CCTV, voice-recording verification, external SPIV/HO confirmation, SmartFX/CBS/Pega lookups, external signature specimens, physical stamp authenticity/inventory and actual employee/presenter authority checks are excluded from executable SOP checks and scores. An excluded requirement does not generate an SOP REVIEW or FAIL penalty.

A source instruction may contain both document observations and excluded requirements. Each source catalog entry records the retained document portion and excluded components. A document observation does not claim to verify the entire original control.

Native engine quality findings are preserved separately under **Document Quality** in XLSX and `technical_findings` in JSON. They do not enter SOP scores. Processing and classification errors still block final release. The standalone engine retains its full native validation behavior; the platform's SOP scope is a separate control layer.

### Supported comparisons and conservative outcomes

| Preset | Behavior |
| --- | --- |
| required / document_required | Checks one unambiguous completed document field or required document |
| match_exact | Case/whitespace-normalized text equality; identifiers retain character case and leading zeros |
| match_address / match_purpose | Exact normalized equality passes; different prose requires review rather than invented semantic equivalence |
| date_equal / date_on_or_after | Compares normalized valid DD-MM-YYYY dates |
| match_money | Compares positive Decimal principal values plus explicit ISO currency companions |
| signature_visible | Requires explicit visible handwritten/non-text and completeness observations with page/region evidence |
| all_pages_marked | Checks unique physical page observations, configured expected page count and bottom-right marks |
| stamp_present / stamp_placement | Checks document visibility/completeness and, when requested, signer-region placement |
| signature_visual_consistency | Remains REVIEW until a reviewer inspects both supplied document signing regions; presence booleans cannot pass it |
| policy_review | Retains unresolved policy/components transparently until an approved configuration or reviewed document observation resolves them |

Missing/ambiguous references and low-confidence sources produce REVIEW. Conditions with unknown case context produce REVIEW, not an assumed NOT_APPLICABLE. Neither signature identity nor physical stamp authenticity is inferred.

The initial rule package includes executable comparisons and explicit policy-review placeholders covering every eligible source entry. These placeholders are intentionally **not a claim of a completed bank-approved policy package**. Before ordinary automatic operation, an authorized bank administrator must configure the retained document controls and approve ambiguous mappings. Unresolved policy components can be recorded as case-specific document observations by reviewers, with provenance; they are not automatically passed.

### Explicit case context

The context form supports transaction direction, threshold state, customer type, identity type, declared carrier and payment basis, plus transaction inputter/approver names. An annotation records actor, reason, document evidence and time. It does not query external monthly turnover or infer a funding currency from the purchased currency.

Important policies remain explicit:

- SOP1 No.9 refers to invoice date, while SOP2 No.9 refers to due date. The starter package does not select one silently.
- SOP3 No.6 has an ambiguous sender/recipient ownership mapping. The starter rule remains REVIEW until an approved mapping is configured.
- SOP3 No.14 cannot compare invoice number numerically with an amount. Linkage and amount basis need distinct rules/observations.
- Valas 2 has no usage amount or purpose. SOP3 Nos.10 and 12 are NOT_APPLICABLE when only that declaration variant is present.
- Invoice comparisons use explicit FULL_INVOICE or PROGRESS_CLAIM basis. Progress claims compare claim amount/currency; partial payments require review and a separately approved basis.
- Individual identity requirements must be configured for the individual or authorized representative; a company is not itself an eKTP holder.

## Case processing and traceability

`DocumentWorkflow` continues to run document activities in parallel. Completion queues `CaseRun` only when no document remains active. `CaseSOPWorkflow` then evaluates frozen inputs and writes report artifacts. The Temporal ID is `sop-{case_id}-{snapshot_hash}-{configuration_version}`. The development runner uses leased, conditional database claims for both job types.

The snapshot includes membership, document hashes, raw/normalized values, overrides, metadata, provider IDs, pinned configuration/schema hashes and context. The worker rechecks the fingerprint before evaluation and before publication. Superseded runs do not publish a stale current report. Identical input reruns are idempotent.

Field corrections use stored raw extraction. **Rerun SOP checks** uses stored normalized values and rules; neither action creates another paid extraction. Context changes create a new snapshot/report revision. A failed SOP/report activity is visible in case progress and inbox; retry resumes the case job, preserving completed document extraction. Paid provider submissions retain their existing checkpoint/reconciliation behavior.

A reviewed observation records PASS/FAIL, rationale, actor and supplied-document/page/region references. Signature consistency requires both relevant document observations. Decisions are bound to the document/configuration fingerprint. Changing document inputs prevents an old observation from being reused; changing case context clears prior observations. The original automated REVIEW remains traceable in the report.

The UI polls while visible, refreshes on focus, shows pending actions and notifications, and leaves worker processing independent of the browser. This release uses polling rather than SSE.

## Kertas Kerja

The main XLSX follows the supplied A–T layout and header context. It excludes original sample customers, discussion notes and invalid fixed total ranges. One case occupies one row and **Data Count = 1**. Account numbers remain strings.

| Columns | Source / meaning |
| --- | --- |
| A–C | Row number, confirmed finding status and case count |
| D–F | Remitter/customer name, remitter account and transaction type |
| G–I | Explicit transaction inputter/approver and declared carrier; never substituted with uploader/platform reviewer |
| J–K | Transaction date and SOP inspection date |
| L–M / N | Data Completion, Customer Signature / Total A |
| O–P / Q | Document Completion, Officer Review & Approval / Total B |
| R | Overall score |
| S | Original BIC Remarks: blank and hidden |
| T | Deterministic categorized Product Remarks from eligible findings |

A category is **0** for any confirmed eligible FAIL, **1** when all applicable checks resolve PASS, and blank for unresolved REVIEW/ERROR/no applicable controls. A confirmed zero dominates aggregates; otherwise unresolved operands leave totals blank. NOT_APPLICABLE is omitted from the scored set. Only eligible active SOP findings affect scores.

Scores and summary percentages are numeric server-computed values, not formulas requiring Excel recalculation. Percentages use scored cases as the denominator. Total cases, scored cases and unresolved cases are displayed together. A branch export uses each case's latest **saved** report snapshot, so it can include drafts and older snapshots while a new revision is processing; review its state/configuration/hash in Report Trace and SOP Details.

Additional sheets retain all SOP results including PASS, source/scope/category, actual/expected values, evidence, native document quality, extracted/raw/override values and report trace. Individual reports have immutable versioned PDF/XLSX/JSON artifacts in MinIO. Branch XLSX exports store a manifest of report IDs/versions/hashes and an audit record.

Report finality is separate from compliance: an authorized reviewer may release a completed report containing confirmed FAIL findings. Missing required documents, processing errors or unresolved SOP reviews block release. Maker/checker separation applies when configured. Final release does not erase violations.

## API additions

- `GET /api/config/catalog` — typed fields, eligible source catalog, operators and context options.
- `GET /api/config/export` — current editable XLSX; bank administrator.
- `POST /api/config/import` — multipart XLSX → validated draft or row/cell errors; bank administrator.
- `POST /api/config/test` — native replay plus case SOP replay, without paid jobs or publication.
- `PUT /api/cases/{id}/context` — audited values/reason/evidence → new case SOP snapshot.
- `POST /api/cases/{id}/sop-rerun` — idempotent rerun/retry using stored extraction.
- `POST /api/cases/{id}/sop-review` — reviewer decision with supplied-document observations.
- `GET /api/reports/kertas-kerja?branch_id=...` — scoped branch XLSX and stored export manifest.

## Upgrade

Back up the database and MinIO, stop API/workers, and run `python backend/migrate_profiles.py` using the configured project environment. The script publishes missing profiles and the new automation configuration as a **new version** without modifying historical versions. API startup creates the two additive tables (`case_contexts`, `case_runs`); no existing columns are rewritten. Development startup upgrades automatically for the development organization.

Historical cases keep their legacy workflow/report behavior. New automation cases require a new upload using the upgraded version. A production deployment should replace development `create_all` with its controlled database migration process. Existing immutable report snapshots remain readable.

## Verification and boundaries

See `VERIFICATION.md` for this build's checks. Fixture and mocked provider tests do not establish OCR accuracy. Real LlamaCloud extraction must still be evaluated with the bank's samples and scoped API key. Docker/real PostgreSQL/MinIO deployment testing and Windows launcher execution are not asserted by the isolated tests.

Production SSO, PostgreSQL RLS, approved infrastructure/retention, quotas, a visual page-layout designer and advanced inbox assignment/SLA controls remain deployment work. External verification is explicitly outside this SOP scope. The supplied source workbooks establish the controls and report mapping; they do not supply all master lists, policy interpretations or visual authenticity evidence.
