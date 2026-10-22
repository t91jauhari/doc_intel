# v0.3 update

See [release notes](docs/RELEASE_0_3.md) for the current evidence/RIPLAY behavior and remaining tasks.

# SQE Document Automation Platform

Runnable v0.2.1 development release: FastAPI API, separate Python workers, Next.js UI, seven extraction profiles, document-only SOP checks, workbook configuration, independent case workflows and versioned Kertas Kerja.

Read [the automation guide](docs/AUTOMATION_GUIDE.md) for the new workflow, SOP editor, templates and report behavior. [Verification](docs/VERIFICATION.md) records tested behavior and current limits.

## v0.2.1 Windows fix and automated verification

Explicit UTF-8 catalog reads fix the reported Windows charmap error. See [development and verification](docs/AUTONOMOUS_DEVELOPMENT.md) for upgrade instructions, the approved task queue and the one-command browser release gate.

## Start immediately

### Windows — local development

Install Python 3.12+, Node.js 24 LTS and Docker Desktop (running), extract this folder, then double-click **start.bat**.

Or use PowerShell from the project folder:

    py -3 scripts/run_dev.py

The launcher creates an isolated Python environment, installs dependencies on the first run, starts MinIO through Docker Compose, starts the API and independent worker, and starts Next.js.

Open **http://localhost:3000**.

| Login field | Value |
| --- | --- |
| Organization | sqe |
| Email | sqe@bic.local |
| Password | P@ssw0rd2026 |

The seeded development account is a bank administrator. Passwords are salted and hashed. The password is not hardcoded into the frontend.

Press Ctrl+C in the launcher terminal to stop local services.

### Linux / WSL — local development

    bash start.sh

### Docker Compose

Install Docker with Compose, then run:

    python scripts/init_dev.py
    docker compose up --build -d

Use the same login at http://localhost:3000.

Compose runs MinIO, PostgreSQL, a persistent Temporal development service, the API, independent worker and Next.js. The Temporal development UI is at http://localhost:8233.

Scale workers independently:

    docker compose up -d --scale worker=3

Each worker defaults to four concurrent document activities. Set WORKER_CONCURRENCY in .env before restarting workers to change that infrastructure limit.

View logs:

    docker compose logs -f api worker web

Stop without deleting data:

    docker compose down

Generated .env files, databases, sessions, uploaded files and connector secrets are excluded from the source package. init_dev.py creates a new APP_SECRET, database password and MinIO secret once. On upgrade it adds missing MinIO settings while retaining existing values.

## Real LlamaCloud processing

1. Sign in.
2. Open **Configuration → Connector**.
3. Save the same working LlamaCloud API key used by your SDK example.
4. Leave base URL, project scope and provider organization scope blank unless your account requires them.
5. Keep **Configuration → Workflow → Provider** set to LlamaCloud.
6. Upload customer documents.

Parse and extraction default to agentic_plus. The provider adapter uses llama-cloud 2.16.0, matching the existing engine.

The organization name sqe belongs to the application and is independent of any LlamaCloud organization ID.

## Test without API credits

1. Open **Configuration → Workflow**.
2. Select **Synthetic fixtures · development only**.
3. Click **Publish settings**.
4. Upload PDFs with recognized suffixes.

Fixture mode uses explicitly synthetic extraction values. It does not classify or extract uploaded document content. Reports and case views label these results as development fixtures.

Existing cases retain their original provider configuration. To test fixture mode, create a new upload after publishing the fixture configuration.

Included PDF samples are in engine/samples/. These can be used to exercise upload and real processing. Synthetic fixtures are separate JSON files in backend/fixtures/.

## Confirmed grouping and classification mechanism

**Filename customer grouping happens first. LlamaCloud Classify happens afterward for every document.**

Examples:

    poko_transaction.pdf
    poko_lld.pdf
    poko_invoice.pdf

These files group into one Poko case within the selected branch and upload batch.

The platform also recognizes configured labels such as:

    Forex - Poko - Aplikasi Transaksi.pdf
    Forex - Poko - LLD.pdf
    Forex - Poko - Invoice.pdf

The preview displays editable customer labels before upload. Case and document memberships are persisted before any processing job is queued.

Grouping uses normalized case and spacing. It does not fuzzy-merge customer names or merge historical cases automatically.

Later uploads create new cases unless explicitly attached through **Case → Add documents**. Multiple transactions for the same customer within a single batch require distinct case labels; customer name alone cannot distinguish them.

The filename's document suffix is a hint. LlamaCloud verifies the actual content before extraction. Low confidence, unsupported types and filename/content disagreements wait for review. A reviewer can confirm the type and record the reason.

This release intentionally uses a profile-specific parse after classification, because the classifier's generic parse is not assumed to satisfy the engine's specialized form prompts. Extraction reuses that specialized parse job ID. Classification can therefore incur its own parsing charges.

| Suffix | Profile |
| --- | --- |
| _transaction.pdf | Application of Transaction |
| _lld.pdf | LLD |
| _invoice.pdf | Underlying Invoice |
| _valas1.pdf | Valas declaration 1 |
| _valas2.pdf | Valas declaration 2 |
| _ektp.pdf | eKTP |
| _riplay.pdf | RIPLAY Document (4 pages) |

Document labels, prompts, policies and classification threshold are configurable.

## Implemented workflow and screens

- Login with organization-scoped accounts and HttpOnly sessions.
- Operations cockpit with counts and recent cases.
- Bulk PDF upload with progress and customer-group preview.
- Branch-scoped case list.
- Case workspace with document statuses, extracted values, raw evidence and findings.
- Manual type confirmation, field corrections, document moves and safe retries.
- Persistent case inbox; marking read does not resolve findings.
- Versioned PDF, Excel and JSON kertas kerja downloads.
- CSV exports grouped separately by document type.
- Configuration publication and read-only replay tests against stored extraction.
- Six profile prompts and the existing validation policies.
- Typed document-only SOP rules from the approved YES catalog and all SOP3 system controls; configuration workbook import/export and case replay.
- Branch creation and multi-branch user creation.
- Roles: bank administrator, branch administrator, officer, reviewer and auditor.
- Optional maker–checker release restriction.

The Forex starter template currently requires Application, LLD and Invoice. This is an editable development template, not an assertion of the bank's final document checklist. Configure the 4–7 document requirements using your approved reference.

Reports are generated even when validation fails or requires review. The latest complete report may be released with confirmed FAIL findings; unresolved reviews, processing errors and missing required documents block release. External verification and CCTV are excluded from SOP execution/scoring. Ambiguous document-only policy requirements remain REVIEW.

## Processing, retries and audit

The API queues durable database jobs. The Temporal dispatcher uses stable workflow IDs; independent workers execute document workflows and then a separate case SOP/report workflow.

The local launcher uses a DB-leased development runner so Docker/Temporal are not required for the first local test. This driver is disabled outside development.

Provider file, classification, parse and extract job IDs are checkpointed. Repeated processing resumes known jobs.

A creation is marked pending before calling the provider. If its outcome is uncertain, the app blocks a blind resubmission. A bank administrator can reconcile the existing provider ID with a recorded reason.

Known failed remote jobs retain their job IDs. A retry does not silently create a replacement paid job.

Raw extraction is stored before validation. Field corrections are separate overrides; they rerun validators without another cloud extraction.

Cases pin their configuration version. Publication changes new cases only. Reports preserve immutable evaluation snapshots, and approval is recorded separately.

The UI polls fresh server snapshots while the page is visible and refreshes on focus. This development release uses polling rather than SSE; processing remains independent of the browser.

## Project structure

    backend/app/
      main.py          API and authorization boundaries
      db.py            Persistence models
      security.py      Passwords, sessions, scope checks and secret encryption
      domain.py        Configuration, grouping, SOP evaluation and report snapshots
      provider.py      LlamaCloud adapter and side-effect checkpoints
      processor.py     Document processing and failure recording
      sop.py           Typed SOP contracts, allowlist, evaluator and scoring
      config_workbook.py XLSX draft import/export
      case_processing.py Frozen case SOP jobs and report orchestration
      kertas_kerja.py   Main layout and server-computed scores
      workflow.py      Temporal document and case workflows
      worker.py        Temporal worker/dispatcher and local development runner
      reporting.py     PDF, Excel and JSON report rendering
    backend/tests/     Platform and Temporal integration tests
    backend/fixtures/  Explicit synthetic development extraction responses
    frontend/app/      Next.js screens and styles
    frontend/components/
    frontend/lib/
    engine/            Existing seven-profile extraction engine
    scripts/           Initialization, launcher and browser smoke test
    compose.yaml       Multi-service development deployment
    ARCHITECTURE.md     Full plan plus confirmed development decisions

## Verification

Backend:

    cd backend
    ../.venv/bin/python -m pytest tests -q

Windows equivalent:

    ..\.venv\Scripts\python.exe -m pytest tests -q

The Temporal integration test downloads and starts the official test service when not cached.

Existing engine regression tests:

    cd engine
    ../.venv/bin/python -m unittest discover -s tests -q

Frontend:

    cd frontend
    npm run typecheck
    npm run build

Browser smoke test, from the project root after building the frontend:

    cd frontend
    npx playwright install chromium
    cd ..
    node scripts/browser_smoke.mjs

The browser test starts isolated services and a temporary database, uses fixture mode, and checks login, workbook import/export, typed SOP editing, replay/publication, grouping, case worker completion, context correction, findings, inbox and PDF/branch XLSX downloads. Screenshots are saved under data/browser-checks/. It creates no billable provider jobs.

## Development release boundary

This is a working development foundation. Before a bank production deployment, complete the deployment-specific SSO integration, controlled database migrations and PostgreSQL RLS, production MinIO provisioning, retention/backup policies, branch fairness/provider quotas and approval of the bank's document-only policy interpretations. External verification is excluded from this release's SOP scope.

Business configuration supports the operators exposed in this release. More specialized checks should be reviewed domain modules. A full visual page-layout designer and advanced notification assignment/SLA policies are subsequent increments.

Compose uses Temporal start-dev and a single-node MinIO service with a persistent volume. They are appropriate for development; production must use the approved managed or self-hosted Temporal/storage deployment.

No live paid LlamaCloud run is claimed without a supplied API key. Fixture, provider-contract and orchestration tests do not establish OCR accuracy against real scans.


## MinIO document and report storage

MinIO is the default file backend for both API and workers. Originals are stored before any document workflow is queued. Each completed case SOP evaluation stores configured PDF/XLSX formats plus JSON trace artifacts (error-case artifacts are deferred until download after recovery); approval stores separate final artifacts. Raw extraction and frozen report snapshots remain in PostgreSQL. CSV exports are generated on request per document type.

The bucket is private. Users access PDFs/reports through authenticated API endpoints with organization/branch authorization. Credentials are server-side only. Storage keys include organization, original branch and document/report ID, avoiding customer names. Original object keys are retained when a document moves to another case; access follows its current database authorization. Moving a document across branches remains unsupported.

| Setting | Development default |
| --- | --- |
| STORAGE_DRIVER | minio |
| MINIO_ENDPOINT | localhost:9000; minio:9000 inside Compose |
| MINIO_ACCESS_KEY | sqe-dev |
| MINIO_SECRET_KEY | Generated once in .env |
| MINIO_BUCKET | sqe-documents |
| MINIO_SECURE | false for local development |
| MINIO_REGION | us-east-1 |

MinIO console: http://localhost:9001. Sign in with MINIO_ACCESS_KEY and MINIO_SECRET_KEY from .env; this account differs from the application's SQE login. Development Compose uses these as MinIO root credentials. Production must use a separately provisioned application access key limited to its bucket, TLS, an approved MinIO release/deployment, backup and retention policies. The application does not set public bucket policies. Only development creates missing buckets.

Local launchers start the MinIO service automatically. To use an existing MinIO deployment, configure the variables above and set MINIO_MANAGED_EXTERNALLY=1 before running the launcher. STORAGE_DRIVER=local remains available for isolated development/testing. API and workers no longer share a file volume in Compose.

### Upgrade existing local files

Stop API/workers, keep the original DATABASE_URL and STORAGE_PATH, configure the target MinIO server, then run from the backend folder using the project's Python environment:

    python migrate_storage.py

The migration verifies document SHA-256 checksums before and after upload, records immutable original keys, and exports existing report snapshots. It leaves the old files intact and can be rerun. Copying the former Docker documents volume requires making its files accessible as STORAGE_PATH. Do this before processing old cases with the new build. There is no silent fallback to local storage when MinIO is unavailable.


## RIPLAY four-page profile

RIPLAY is supported in classification, extraction, native validation, SOP checks, settings, reports and its own CSV export. The ten requested fields include separate customer/officer signatures and stamps, creation/print dates, and explicit bottom-right mark observations for all four physical pages. Dense product prose is retained as document context and does not supply entered values. Parse and Extract use the existing agentic_plus defaults.

The attached sample is engine/samples/indah_laruna_riplay.pdf. Detailed instructions, schema and policies are in engine/riplay/README.md. For a direct engine test, enter engine/ and run:

    python run.py --document-type riplay --pdf samples/indah_laruna_riplay.pdf --parse-tier agentic_plus --extract-tier agentic_plus

In the platform upload customer_riplay.pdf alongside customer_ektp.pdf using the same customer label. The SOP checker compares RIPLAY customer name with the eKTP name from that case; missing/ambiguous reference triggers review. It never overwrites either identity.

Development startup adds the new profile through a new configuration version. For other deployments, stop API/workers and run backend/migrate_profiles.py using the configured environment, then restart. Existing case versions remain pinned; new document types require a new case using the latest configuration.

Stamp rules 18 and 5 remain unconfigured until you provide their text or set approved policies. Signature visibility is checked; correspondence to a named signer requires external reference evidence and is REVIEW by default. There is no signature-comparison connector in the current platform. The sample's print date precedes its signing date, so the supplied date rule will flag it. Read the profile README for the optional final-page main-signature exception; it is disabled by default.
