# PROJECT_INDEX — Document Intelligence Platform

> Repo inventory, per-module logic, and cross-module interaction map for the
> SQE Document Automation platform (backend FastAPI + standalone extraction
> engine + Next.js frontend).

---

## 1. Overview

The platform automates bank document review for Forex transactions and Account
Opening. A reviewer uploads a batch of customer PDFs; the system groups them by
customer, classifies each document type, extracts structured fields via
LlamaCloud (or an image-only Spider-AI alternative), normalizes and validates
them, evaluates SOP compliance rules, and produces a *Kertas Kerja* (worksheet)
report for release.

**Tech stack**

| Layer        | Technology                                                        |
| ------------ | ----------------------------------------------------------------- |
| Backend API  | Python 3.12, FastAPI, Uvicorn                                     |
| ORM          | SQLAlchemy 2.x (core + ORM, `SessionLocal`, no Alembic)           |
| Database     | PostgreSQL 17.6 (SQLite in dev/test)                             |
| Object store | MinIO (S3-compatible)                                             |
| Workflow     | Temporal 1.6.2 (dev mode) or local DB-leased runner              |
| Extraction   | LlamaCloud SDK (`llama-cloud==2.16.0`) or OpenAI-compatible API  |
| Frontend     | Next.js 14+ (App Router), React, TypeScript, standalone output    |
| PDF imaging  | PyMuPDF (`fitz`), Pillow                                          |
| Reports      | openpyxl (XLSX), ReportLab (PDF), JSON                            |

---

## 2. Repository Tree

```
document-platform/
├── compose.yaml                         # 6-service Docker Compose
├── README.md  ARCHITECTURE.md  VERIFICATION.md
├── _enum.py  _tree.txt                  # Enum patch utility, cached tree
├── start.bat / start.sh                 # Dev launchers
├── PATCH_0_3_*.md … PATCH_0_6_7.md      # 24 patch changelogs
├── PATCH_MANIFEST_0_4_0.json … 0_6_7    # 13 patch manifests
├── UX_REVIEW_0_5_2.md
│
├── backend/
│   ├── Dockerfile                       # Python 3.12-slim, copies app + engine
│   ├── requirements.txt
│   ├── generate_templates.py            # PDF template generation
│   ├── migrate_profiles.py              # Profile migration
│   ├── migrate_storage.py               # Storage migration
│   ├── operations/  backup.py  migrate_003.py  retention_inventory.py
│   ├── fixtures/                        # 13 JSON test fixtures (per doc type)
│   ├── tests/                           # 23 test files + conftest.py
│   └── app/  ← 43 Python modules (see §4)
│       ├── config_data/                 # 7 JSON catalogs
│       └── datasets/                    # forex_sample.json, account_opening_sample.json
│
├── engine/                              # Standalone extraction CLI (LlamaCloud)
│   ├── run.py  batch.py  profiles.py  schema.py  validation.py  context.py
│   ├── valas_common.py  name_directory.json  policy.json
│   ├── samples/  tests/  (9 test files)
│   └── account_opening/  ektp/  invoice/  lld/  riplay/  valas1/  valas2/
│
├── frontend/
│   ├── Dockerfile                       # Node 24-alpine, multi-stage standalone
│   ├── app/                             # Next.js App Router (7 routes)
│   ├── components/                      # 17 React components
│   └── lib/  api.ts  types.ts  document-family.ts  extraction-export.ts
│
├── docker/minio/                        # Custom MinIO build context
├── infra/temporal.Dockerfile            # temporalio/temporal:1.6.2
├── docs/                                # Automation guide, release notes, etc.
├── scripts/  init_dev.py  run_dev.py  verify.py  browser_smoke.mjs
├── benchmarks/  manifest.json  expected-fields.csv
└── templates/  forex-kertas-kerja-template.xlsx  forex-workflow-config-template.xlsx
```

---

## 3. Infrastructure & Deployment

### Docker Compose (`compose.yaml`)

Six services with health-gated dependencies:

| Service   | Image / Build                | Port  | Role                                      |
| --------- | ---------------------------- | ----- | ----------------------------------------- |
| `postgres`| `postgres:17.6`              | —     | Business state, read model, audit trail   |
| `minio`   | Custom (`docker/minio`)      | 9000  | S3-compatible object store for PDFs/evidence |
| `temporal`| `temporalio/temporal:1.6.2`  | 8233  | Durable workflow orchestration (dev mode) |
| `api`     | `backend/Dockerfile`         | 8000  | FastAPI / Uvicorn — REST API              |
| `worker`  | `backend/Dockerfile`         | —     | `python -m app.worker` — job processor    |
| `web`     | `frontend/Dockerfile`        | 3000  | Next.js standalone server                 |

**Volumes:** `postgres`, `minio`, `temporal` (persistent data).

**Environment wiring:**
- `DATABASE_URL=postgresql+psycopg://sqe:…@postgres:5432/sqe`
- `STORAGE_DRIVER=minio`, `MINIO_ENDPOINT=minio:9000`, `MINIO_BUCKET=sqe-documents`
- `WORKFLOW_DRIVER=temporal`, `TEMPORAL_ADDRESS=temporal:7233`
- All services share `.env` via `env_file`.

### Backend Dockerfile

```dockerfile
FROM python:3.12-slim
COPY backend/app /app/backend/app
COPY backend/fixtures /app/backend/fixtures
COPY engine /app/engine                          # ← engine on PYTHONPATH
RUN PYTHONPATH=/app/backend:/app/engine python -c "from app.reporting import make_report; …"
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
```

The `engine/` package is copied into the image and placed on `PYTHONPATH`
alongside `backend/`. This is how `main.py` can do `from validation import
check_schema` and `domain.py` can do `from context import check_directory`.

### Frontend Dockerfile

Multi-stage Node 24-alpine build. `npm run build` produces a standalone output
(`.next/standalone`), copied to the run stage. `API_INTERNAL_URL=http://api:8000`
is baked at build time for server-side fetches.

### Temporal Dockerfile

`temporalio/temporal:1.6.2` with a `/var/lib/temporal` volume. Runs in dev mode
(`server start-dev`) with a SQLite database file — suitable for development, not
production durability.

---

## 4. Backend Architecture (`backend/app/`)

43 Python modules organized into functional layers.

### 4.1 Entry Point & API Layer — `main.py` (~2627 lines)

The FastAPI application. Defines every REST endpoint under `/api/*`.

**Lifespan:** On startup, calls `domain.seed()` to create the default
organization, admin user, branches, and initial configuration version if the
database is empty. Initializes `WorkerSlot` capacity slots.

**Endpoint groups:**

| Prefix                          | Methods | Purpose                                      |
| ------------------------------- | ------- | -------------------------------------------- |
| `/api/auth/{login,logout,session}` | POST/GET | Session auth, CSRF token issuance           |
| `/api/branches`                 | GET/POST| Branch CRUD (bank_admin only)                |
| `/api/users`                    | GET/POST| User CRUD with role/branch assignment        |
| `/api/config{,s}`               | GET/POST| Config publish (versioned), draft, import/export XLSX |
| `/api/uploads`                  | POST    | Idempotent batch upload (`Idempotency-Key`), grouping, case creation |
| `/api/documents/{id}/...`       | GET/POST| File download, retry, classification, corrections, evidence |
| `/api/cases/{id}/...`           | GET/POST| Case detail, comparison, SOP rerun/review, enum revalidation |
| `/api/reports{,/{id}/...}`      | GET/POST| Report list, download (pdf/xlsx/json), approve (FINAL) |
| `/api/reports/kertas-kerja`     | GET     | Branch-level Kertas Kerja XLSX export        |
| `/api/exports/{doc_type}`       | GET     | CSV export of completed documents by type    |
| `/api/inbox` `/api/audit` `/api/dashboard` `/api/health` | GET | Inbox, audit log, stats, health |

**Authorization:** `Depends(current_user)` on every endpoint. Role-based
dependencies: `WRITE` (excludes auditor), `REVIEW` (bank_admin, branch_admin,
reviewer). `authorized(db, Model, id, user)` scopes every query by org + branch.

**Concurrency:** Uses `select(…).with_for_update()` (row-level locks) on Case,
Document, CaseContext, DatasetComparison, and CaseRun to serialize concurrent
writes. Idempotent uploads via `Idempotency-Key` header → `Batch` table lookup.

### 4.2 Core Domain Logic — `domain.py` (~845 lines)

The business brain. Key responsibilities:

1. **Engine path initialization** (lines 32–37): Inserts `engine/` onto
   `sys.path`, then imports `context.check_directory`, `profiles.get_profile`,
   and `account_opening.profiles.REFERENCE`. This bridges the standalone engine
   into the backend.

2. **Filename routing & classification** (`route()`): Maps filenames to document
   types via suffix matching (`SUFFIXES` dict). Returns `(hint, customer_name,
   classification)`.

3. **Config validation** (`validate_config()`): Validates the full configuration
   payload — profiles, templates, sop_rules, workflow, report mappings. Calls
   `sop.validate_business()`, `transaction_flows.validate_flows()`.

4. **Config versioning** (`publish_config()`): Creates a new immutable `Config`
   row with incremented version. Old versions are never mutated; existing cases
   retain their pinned `config_id`.

5. **Riplay identity matching**: Matches RIPLAY documents to customer cases
   using identity tokens (name, NIK) with conservative conflict detection.

6. **SOP rule evaluation**: Delegates to `sop.evaluate()` for rule checking and
   `sop.score()` for category rollup.

7. **Report snapshot building**: Assembles the full report snapshot (documents,
   findings, scores, missing, validation_status, customer, provider,
   technical_findings) from case inputs.

8. **Audit logging** (`audit()`): Writes `Audit` rows for every state-changing
   action with org, actor, event, branch_id, case_id, and detail kwargs.

9. **Seeding** (`seed()`): Creates default org (`sqe`), admin user, branches,
   and initial config from `sop.defaults()` + engine profiles.

### 4.3 Data Model — `db.py`

SQLAlchemy ORM with `Base.metadata.create_all()` (no Alembic migrations).
`SessionLocal` is a session factory; `engine` is the global engine.

**Tables (17 models):**

| Model               | Key columns                                                    |
| ------------------- | ------------------------------------------------------------- |
| `User`              | id, org, email, password_hash, name, role, branches (JSON), active |
| `Branch`            | id, org, code, name                                            |
| `Config`            | id, org, version, payload (JSON), created_at                   |
| `Case`              | id, org, branch_id, reference, customer, template, config_id, status, validation_status, created_by |
| `Document`          | id, org, branch_id, case_id, batch_id, filename, sha256, doc_type, status, classification (JSON), raw (JSON), normalized (JSON), overrides (JSON), validation (JSON), metadata_json (JSON), provider_state (JSON), error |
| `Job`               | id, document_id, status, lease_until                           |
| `Report`            | id, org, branch_id, case_id, version, fingerprint, snapshot (JSON), state, approved_by |
| `CaseRun`           | id, org, branch_id, case_id, fingerprint, snapshot (JSON), status, stage, error, lease_until |
| `CaseContext`       | id, org, branch_id, case_id, payload (JSON)                    |
| `CaseTask`          | id, case_id, payload (JSON), status                            |
| `Inbox`             | id, org, branch_id, case_id, title, body, severity, read, resolved, assigned_to, due_at |
| `Audit`             | id, org, branch_id, case_id, actor, event, details (JSON), created_at |
| `Batch`             | id, org, branch_id, key, created_at                            |
| `DatasetComparison` | id, case_id, payload (JSON), revision                          |
| `LocationFeedback`  | id, org, branch_id, document_type, feedback (JSON)             |
| `WorkerSlot`        | id (1–50), owner, lease_until                                  |
| `Connector`         | id, org, type, config (JSON)                                   |
| `SpiderConnector`   | id, org, config (JSON)                                         |

**JSON columns** store semi-structured data (extraction results, validation
issues, provider state, config payloads). No relational foreign-key constraints
are declared; relationships are enforced at the application layer.

### 4.4 Document Processing Pipeline

**`processor.py`** — Orchestrates the per-document lifecycle:
`classify → parse → extract → normalize → validate`. Calls the provider for
cloud extraction, generates visual evidence crops, runs engine validation, and
persists results to `Document.raw`, `.normalized`, `.validation`.

**`provider.py`** — LlamaCloud provider. Uploads PDF once, configures Parse
(Indonesian + English OCR, form enrichment, layout), passes the completed Parse
job ID to Extract. **Durable checkpointing**: saves Parse/Extract job IDs to
`Document.provider_state` so interrupted jobs can resume without duplicate
cloud submissions. SDK retries are disabled to prevent blind duplicate creation.

**`spider_provider.py`** — Alternative image-only extraction via an
OpenAI-compatible API. Renders PDF pages to images (PyMuPDF), base64-encodes
them, and submits with durable submission checkpoints. Used when
`cfg.provider == "spider-ai"`.

**`spider_result.py`** — Formats Spider extraction results without native
normalization; reviewer overrides are applied as explicit audited inputs.

**`spider_riplay.py`** — Sequential image extraction for multi-page RIPLAY
documents with lossless per-page results and conservative merging (conflicts
flagged, never silently resolved).

**`spider_config.py`** — Seeds Spider instructions into config immutably without
changing the active provider setting.

**`provider_errors.py`** — Sanitizes API error diagnostics: redacts bearer
tokens, API keys, and URLs; truncates to 1200 chars. Only allows safe fields
(`message`, `detail`, `code`, `type`, `loc`, `msg`).

### 4.5 SOP Evaluation & Case Orchestration

**`sop.py`** (~577 lines) — The SOP rule evaluation engine.

- **CATEGORIES**: `DATA_COMPLETION`, `CUSTOMER_SIGNATURE`,
  `DOCUMENT_COMPLETION`, `OFFICER_REVIEW_APPROVAL`.
- **OPERATORS**: `required`, `match_exact`, `match_address`, `match_purpose`,
  `match_money`, `date_equal`, `date_on_or_after`, `document_required`,
  `signature_visible`, `signature_visual_consistency`, `all_pages_marked`,
  `stamp_present`, `stamp_placement`, `account_check`, `policy_review`.
- **`evaluate()`**: Runs each rule against extracted document values. Produces
  findings with `PASS`/`FAIL`/`REVIEW`/`NOT_APPLICABLE` results. Low-confidence
  extraction issues automatically downgrade `PASS`/`FAIL` to `REVIEW`.
- **`score()`**: Rolls up findings per category into 0 (FAIL), 1 (all PASS),
  or null (inconclusive). Computes `total_a`, `total_b`, and `total`.
- **`validate_business()`**: Validates workflow has exactly 9 ordered actions.
- Loads rule/field/scope catalogs from `config_data/*.json`.

**`case_processing.py`** (~353 lines) — Frozen case inputs and SOP/report job dispatch.

- **`inputs(db, case)`**: Snapshots the complete case state (config, documents,
  context, branch) into an immutable frozen dict.
- **`fingerprint(snapshot)`**: SHA-256 hash of the frozen inputs (sorted keys).
  Used to detect superseded runs — if inputs change, the run is marked
  `SUPERSEDED` and a new run is queued.
- **`queue_case(db, case_id)`**: Creates a `CaseRun` with the frozen snapshot
  and fingerprint. Skips if an identical run already exists. Sets case status
  to `SOP_QUEUED`.
- **`run_case(run_id)`**: The worker activity. Evaluates SOP rules via
  `sop.evaluate()`, builds the report snapshot, creates a `Report` version,
  persists report artifacts, and publishes inbox notifications. On fingerprint
  mismatch → `SUPERSEDED`. On exception → `ERROR` with resume capability.
- **`publish_inbox(db, case, count, missing)`**: Creates `Inbox` items for
  ready/review/waiting states.

**`case_context.py`** — Conservative context suggestions. Derives
`threshold_state` (ABOVE/WITHIN from valas declaration variant) and
`customer_type` (INDIVIDUAL from eKTP presence). Conflicts between different
declarations remain ambiguous — never silently picks one.

**`account_opening_sop.py`** — Account Opening SOP controls with 6 categories
(adds `DOCUMENT_VERIFICATION`, `OBSERVATIONS`). Imports `sop.value_at` and
`sop.normalize`.

**`account_opening_report.py`** — Account Opening Kertas Kerja XLSX layout,
preserving evidence sheets and machine snapshots.

**`account_opening_seed.py`** — Seeds Account Opening configuration (rules,
sources, profiles) immutably into a new config version per org. Uses
PostgreSQL advisory locks or SQLite `BEGIN IMMEDIATE` for serialization.

### 4.6 Worker Orchestration

**`workflow.py`** — Defines the 9-step workflow action registry:
`upload → group_by_customer → classify → parse → extract →
normalize_validate → case_sop → render_report → notify`. Each step has an
`order`, `step_id`, `enabled` flag, `preset`, `parameters`, `timeout_seconds`,
`read_poll_retries`, and `on_error` policy. Steps cannot be removed, disabled,
or reordered across dependencies.

**`worker.py`** — The background processor. Entry point: `python -m app.worker`.
- When `WORKFLOW_DRIVER=temporal`: registers Temporal activities for document
  processing and case SOP runs, polls the Temporal task queue.
- When `WORKFLOW_DRIVER=local`: uses a DB-leased loop. Acquires `Job` rows
  (document processing) and `CaseRun` rows (SOP evaluation) via
  `worker_capacity.try_acquire()`, processes them, and releases the lease.
- Calls `processor.process_document()` for document jobs and
  `case_processing.run_case()` for SOP jobs.

**`worker_capacity.py`** — Shared 50-slot lease gate (`WorkerSlot` table, 50
rows). `try_acquire(owner)` atomically claims an idle slot (lease_until ≤ now)
and sets a 900-second lease. `release(owner)` frees the slot. Ensures at most
50 concurrent jobs across all worker replicas. Supports PostgreSQL and SQLite
via dialect-specific upsert (`ON CONFLICT DO NOTHING`).

### 4.7 Object Storage — `storage.py`

Abstraction over MinIO (S3-compatible) and local filesystem.

- **`store()`**: Factory returning a `MinioStore` or `LocalStore` based on
  `settings.storage_driver`.
- **`object_key(org, branch_id, kind, id, filename)`**: Deterministic S3 key
  pattern: `{org}/{branch_id}/{kind}/{id}/{filename}`.
- **`original_key(doc)`**: Key for a document's original PDF.
- **`report_key(report, format)`**: Key for a materialized report artifact.
- **`put(key, data, mime)`** / **`read(key)`**: Store and retrieve bytes.
- MinIO client configured with endpoint, access key, secret key, bucket, secure
  flag from settings.

### 4.8 Reporting & Exports

**`reporting.py`** — `make_report(report, format)` generates reports in JSON,
XLSX, or PDF from a `Report.snapshot`. Persists artifacts to storage via
`persist_report()`. PDF uses ReportLab; XLSX uses openpyxl.

**`kertas_kerja.py`** — Server-computed Kertas Kerja (Indonesian worksheet).
`workbook(snapshots)` builds an XLSX with 20 columns (No, Finding Status,
Customer Name, Account No, Transaction Type, category scores, Total A/B/Total,
BIC/Product Remarks). Uses `sop.CATEGORIES`, `sop.value_at`, and
`value_display.display_value`. Formula-injection protection: cells starting
with `=`, `+`, `-`, `@` are prefixed with `'`.

**`config_workbook.py`** — Bounded XLSX configuration interchange. Export
produces a template workbook with data validation dropdowns. Import returns a
**draft** config — never publishes directly. Uses defined names, data
validation, and styled headers.

**`comparison_excel.py`** — Styled XLSX export of authorized comparison
snapshots. `cell_value()` formats values; MIME constant for content type.

**`value_display.py`** — Human-readable presentation formatting. Indonesian
month names (Januari–Desember), compound value display. Presentation only —
effective values and machine exports remain structured.

### 4.9 Security & Authentication — `security.py`

- **Password hashing**: `hash_password(plain)` / `verify_password(plain, hash)`
  using bcrypt.
- **Session tokens**: Generated on login, stored in HTTP-only cookies. Session
  expiry dispatches a `session-expired` event on the frontend.
- **CSRF protection**: `csrf_token()` generates a per-session token. Every
  mutating request (`POST`/`PUT`/`DELETE`) requires an `X-CSRF-Token` header
  matching the session token. The frontend (`lib/api.ts`) attaches this
  automatically.
- **Field-level encryption**: Fernet symmetric encryption for sensitive config
  values (e.g., API keys in `Connector.config`).

### 4.10 Configuration & Settings — `settings.py`

Environment-driven configuration (no pydantic BaseSettings — plain attributes).

| Setting              | Default                  | Purpose                          |
| -------------------- | ------------------------ | -------------------------------- |
| `ROOT`               | repo root                | Path to project root             |
| `database_url`       | `sqlite:///…`            | SQLAlchemy database URL          |
| `storage_driver`     | `local`                  | `local` or `minio`               |
| `minio_endpoint`     | `localhost:9000`         | MinIO endpoint                   |
| `minio_bucket`       | `sqe-documents`          | MinIO bucket name                |
| `workflow_driver`    | `local`                  | `local` or `temporal`            |
| `temporal_address`   | `localhost:7233`         | Temporal gRPC address            |
| `secret_key`         | —                        | Session signing key              |
| `llama_cloud_api_key`| —                        | LlamaCloud API key               |
| `max_batch_files`    | 50                       | Max files per upload             |

**Production guards**: Warns or errors when running with insecure defaults
(e.g., SQLite in production, missing secret key).

### 4.11 Helper Modules

| Module                       | Purpose                                                      |
| ---------------------------- | ----------------------------------------------------------- |
| `grouping.py`                | Deterministic batch-local customer resolution. `plan_grouping()` routes filenames via `domain.route()`, resolves customer aliases, groups by identity tokens. Abbreviations never bridge people. |
| `grouping_repair.py`         | Repairs one historical batch without repeating provider extraction. |
| `evidence.py`                | Immutable visual crops from explicit provider bounding boxes (PyMuPDF). Never guesses coordinates. `rectangle()` validates bbox format. |
| `field_evidence.py`          | Source crops for populated extraction leaves. `populated_fields()` walks the extraction tree. |
| `parse_evidence.py`          | Links Parse visual/form regions to field names via multilingual aliases (EN/ID). |
| `effective_corrections.py`   | Translates reviewer edits to validated extraction overrides. `extraction_value()` handles numeric text (locale-aware), structured values, checkbox/stamp overrides. Never bypasses normalization. |
| `enum_aliases.py`            | Seeds approved enum spellings (e.g., `KATHOLIK→Katolik`) without changing canonical bank choices. `validate_aliases()` ensures aliases map to valid canonical values. |
| `dataset_comparison.py`      | Independent reference comparisons. Loads forex/account_opening sample datasets. `compare()` produces fuzzy/exact comparison results. Never modifies extraction or SOP decisions. |
| `transaction_flows.py`       | User-managed transaction flow (template) validation. Validates flow IDs, labels, required profiles, document families (`forex`/`account_opening`), dataset IDs, SOP rule IDs. |
| `profile_variants.py`        | Named prompt candidates stored as immutable snapshots. `seed_profile_variants()` creates a new config per org with enhanced profile descriptions/prompts. |
| `location_learning.py`       | Reviewed location retrieval. `LocationFeedback` model stores corrections. Suggestions never become current-document evidence. |
| `schema_descriptions.py`     | Editable extraction instructions with immutable structural engine contract. `contract()` strips descriptions from schema; `validate_descriptions()` checks bounds. |
| `migrate_comparison.py`      | Adds `DatasetComparison` table. Run with workers stopped: `python -m app.migrate_comparison`. |


---

## 5. Engine — Standalone Extraction CLI (`engine/`)

A self-contained Python 3.10+ CLI that wraps the LlamaCloud SDK for PDF
extraction. The backend imports its `validation.py`, `context.py`, and
`profiles.py` modules at runtime (via `sys.path.insert` in `domain.py`).

### 5.1 Core Modules

| Module          | Purpose                                                      |
| --------------- | ----------------------------------------------------------- |
| `run.py`        | CLI entry point: Parse → Extract → validate → CSV export. Supports `--batch`, `--file-id`, `--extract-job-id`, `--replay`, `--dry-run`. |
| `batch.py`      | Batch processing: scans `samples/` for PDFs by suffix, routes to profiles, processes all types. |
| `profiles.py`   | Profile routing. `PROFILE_NAMES` tuple, `get_profile(name)` returns schema/columns/prompts/policy/validator per doc type. |
| `schema.py`     | Application (transaction) extraction schema: 23 semantic fields, nullable evidence, checkbox instructions. `COLUMNS`, `SCHEMA`, `PARSE_PROMPT`, `SYSTEM_PROMPT`. |
| `validation.py` | Deterministic validation. `check_schema()` validates exact types without coercion. `validate()` runs field-level rules. `parse_number()` (locale-aware), `parse_date()` (Indonesian months). Unverifiable rules → `REVIEW`, never implicit `PASS`. |
| `context.py`    | Auditable text correction. `check_directory()` validates bank/branch name directories. `correct_name()` matches aliases. `resolve_checkbox()` reconciles checkbox evidence. |
| `valas_common.py` | Shared logic for Valas Declaration 1 & 2 profiles. |

### 5.2 Document-Type Subpackages

Each subpackage contains `schema.py` (field definitions), `validation.py`
(field-level rules), and sometimes `profiles.py`:

| Subpackage         | Doc type              | Fields |
| ------------------ | --------------------- | ------ |
| `(root)`           | Application           | 23     |
| `lld/`             | LLD                   | 36     |
| `invoice/`         | Underlying Invoice    | 19     |
| `valas1/`          | Valas Declaration 1   | 16     |
| `valas2/`          | Valas Declaration 2   | 10     |
| `ektp/`            | eKTP                  | 20     |
| `riplay/`          | RIPLAY                | —      |
| `account_opening/` | Account Opening forms | —      |

### 5.3 Data Files

- `name_directory.json` — Canonical bank names, branch names, BIC prefixes, aliases.
- `policy.json` — Validation policy parameters.
- `samples/` — Sample PDFs for each document type.

### 5.4 Engine Tests (`engine/tests/`)

9 test files: `test_account_opening_engine.py`, `test_batch.py`, `test_ektp.py`,
`test_invoice.py`, `test_lld.py`, `test_pipeline.py`, `test_riplay.py`,
`test_valas1.py`, `test_valas2.py`. 163 offline tests using mocked LlamaCloud
SDK responses.

### 5.5 Backend ↔ Engine Bridge

```
backend/app/domain.py:
    ENGINE = ROOT / "engine"
    sys.path.insert(0, str(ENGINE))
    from context import check_directory
    from profiles import PROFILE_NAMES, get_profile
    from account_opening.profiles import REFERENCE

backend/app/main.py:
    from validation import check_schema   # engine/validation.py
```

The backend Dockerfile sets `PYTHONPATH=/app/backend:/app/engine`, making both
packages importable. The engine retains its full native validation behavior; the
platform's SOP scope is a separate control layer on top.


---

## 6. Frontend Architecture (`frontend/`)

Next.js 14+ App Router with TypeScript. Standalone Docker output (no Node
server needed beyond `node server.js`).

### 6.1 App Router Routes (`frontend/app/`)

| Route        | File             | Purpose                                      |
| ------------ | ---------------- | -------------------------------------------- |
| `/`          | `page.tsx`       | Dashboard: stats grid, recent cases, config  |
| `/login`     | `login/`         | Sign-in form (org, email, password)          |
| `/upload`    | `upload/`        | Batch PDF upload with grouping preview       |
| `/cases`     | `cases/`         | Case list and case detail (documents, SOP, reports, timeline) |
| `/inbox`     | `inbox/`         | Case exception inbox (paginated)             |
| `/reports`   | `reports/`       | Report list and download (pdf/xlsx/json)     |
| `/settings`  | `settings/`      | Config editor, transaction flows, automation |

**Root layout** (`layout.tsx`): Wraps all pages in `<PlatformProvider>` for
global state (auth, toasts, upload progress). Metadata title:
"SQE · Document Automation".

**Error/loading boundaries**: `error.tsx` and `loading.tsx` at root level.

### 6.2 Global State — `components/platform-provider.tsx`

React Context providing:
- **`user`**: Current authenticated user (null if logged out).
- **`loading`**: Initial session check in progress.
- **`online`**: Browser online/offline status.
- **`toasts`**: Success/error notifications (max 4, auto-dismiss).
- **`upload`**: Upload progress state (`{progress, label, active}`).
- **`signIn(org, email, password)`**: POST `/api/auth/login`, stores CSRF token.
- **`signOut()`**: POST `/api/auth/logout`.
- **`startUpload(form, key)`**: XHR upload with progress, returns
  `{batch_id, case_ids}`.
- **`useData<T>(path, interval=5000)`**: Polling hook. Fetches `/api{path}`
  every 5s when tab is visible. Returns `{data, error, loading, refresh}`.
  Prevents duplicate inflight requests.

Session expiry: listens for `session-expired` window event (dispatched by
`api.ts` on 401), resets user state.

### 6.3 API Client — `lib/api.ts`

- **`api<T>(path, init)`**: `fetch("/api" + path, …)` with `credentials:
  same-origin`, `cache: no-store`. Auto-attaches `X-CSRF-Token` on mutating
  methods. Throws `ApiError(status, message)` on non-2xx. On 401 (not login),
  dispatches `session-expired` event.
- **`uploadFiles(form, key, onProgress)`**: XHR-based upload with progress
  callback. Sets `Idempotency-Key` header for retry safety. Returns
  `{batch_id, case_ids}`.

### 6.4 TypeScript Domain Types — `lib/types.ts`

Mirrors backend models: `User`, `Branch`, `Profile`, `Configuration`,
`CaseSummary`, `CaseDetail`, `Document`, `Finding`, `ReportSnapshot`,
`CaseReport`, `Timeline`, `InboxItem`, `Dashboard`, `WorkflowStep`, `SOPRule`,
`AutomationCatalog`, `FieldCatalog`.

**ProfileName** union: `application | lld | invoice | valas_declaration_1 |
valas_declaration_2 | ektp | riplay | join_visit | edd |
account_opening_form | signature_difference | company_reference`.

### 6.5 Feature Components (`frontend/components/`)

| Component                       | Purpose                                      |
| ------------------------------- | -------------------------------------------- |
| `shell.tsx`                     | Page layout shell (title, subtitle, action)  |
| `ui.tsx`                        | Shared primitives: `Busy`, `Empty`, `ErrorNotice`, `CaseTable` |
| `case-sop.tsx`                  | SOP findings display and review interface    |
| `case-task.tsx`                 | Case task management                         |
| `automation-editor.tsx`         | SOP rule/automation configuration editor     |
| `batch-grouping-repair.tsx`     | Repair historical batch groupings            |
| `copy-extraction.tsx`           | Copy extraction values between documents     |
| `enum-revalidation.tsx`         | Revalidate enum aliases for eKTP             |
| `field-description-editor.tsx`  | Edit schema field descriptions               |
| `grouping-dialog.tsx`           | Document grouping preview/override dialog    |
| `location-learning-history.tsx` | Location feedback history viewer             |
| `profile-version-comparison.tsx`| Compare profile variant versions             |
| `spider-connector.tsx`          | Spider-AI provider connection setup          |
| `spider-resubmit.tsx`           | Resubmit documents to Spider provider        |
| `transaction-flows.tsx`         | Transaction flow (template) manager          |
| `visual-region-editor.tsx`      | Visual evidence region editor                |


---

## 7. Cross-Module Interaction Map

### 7.1 Upload → Case Creation → Processing

```
Frontend (uploadFiles)
  → POST /api/uploads  [main.py]
    → grouping.plan_grouping()           # route filenames, resolve customers
      → domain.route()                   # suffix → doc_type classification
    → storage.put(original_key)          # persist PDFs to MinIO before queuing
    → db: Case, Document, Batch, Job     # create records
    → domain.audit("case.created")
    → worker.enqueue(db, document)       # queue document jobs
      → Job(status="QUEUED")
```

### 7.2 Document Processing (Worker)

```
worker.py (acquires Job via worker_capacity.try_acquire)
  → processor.process_document(document)
    → provider.py (LlamaCloud) or spider_provider.py (Spider-AI)
      → Upload PDF → Parse → Extract (with checkpointing to provider_state)
    → evidence.py / field_evidence.py    # generate visual crops
      → storage.put(evidence_key)        # persist crop images
    → domain.normalize_validate()        # normalize + validate extraction
      → engine validation.check_schema() # schema type validation
      → engine validation.validate()     # field-level rules
    → db: Document.raw, .normalized, .validation, .status="COMPLETED"
  → case_processing.queue_case()         # if all docs complete, queue SOP run
```

### 7.3 SOP Evaluation & Report Generation (Worker)

```
worker.py (acquires CaseRun via worker_capacity.try_acquire)
  → case_processing.run_case(run_id)
    → case_processing.inputs(db, case)   # snapshot frozen inputs
    → case_processing.fingerprint()      # SHA-256 of inputs
    → if fingerprint mismatch → SUPERSEDED, queue new run
    → sop.evaluate(documents, rules)     # run SOP rules → findings
    → sop.score(findings)               # roll up category scores
    → build report snapshot             # documents, findings, scores, missing
    → db: Report(version++, snapshot, fingerprint)
    → reporting.persist_report()        # materialize JSON/XLSX/PDF to storage
    → case_processing.publish_inbox()   # create Inbox items
    → domain.audit("sop.completed")
    → db: Case.status = "READY"|"NEEDS_REVIEW"|"WAITING_DOCUMENTS"
```

### 7.4 Report Review & Release

```
Frontend (case-sop.tsx)
  → POST /api/cases/{id}/sop-review  [main.py]
    → validate finding is eligible & unresolved
    → check fingerprint matches latest report
    → db: CaseContext.payload["rule_reviews"] = {result, observations, …}
    → case_processing.refresh_case()     # re-queue SOP with reviewed context

Frontend (reports page)
  → POST /api/reports/{id}/approve  [main.py]
    → validate: latest report, case READY, no unresolved findings
    → check maker_checker (creator ≠ approver)
    → db: Report.state = "FINAL", Case.status = "FINALIZED"
    → Inbox.resolved = True
    → domain.audit("report.approved")
```

### 7.5 Config Publish Flow

```
Frontend (settings page)
  → POST /api/config  [main.py]
    → domain.validate_config(payload)
      → sop.validate_business()          # 9-step workflow check
      → transaction_flows.validate_flows()  # template validation
      → schema_descriptions.validate_descriptions()
    → domain.publish_config()            # new immutable Config version
    → domain.audit("config.published")
```

### 7.6 Frontend → Backend Data Flow

```
platform-provider.tsx (useData hook)
  → lib/api.ts (api<T>(path))
    → fetch("/api" + path, {credentials: same-origin, cache: no-store})
    → X-CSRF-Token header on mutations
    → 401 → dispatch "session-expired" event → platform-provider resets user
  → polls every 5s when tab visible
```


---

## 8. Authentication & Security Model

### Roles & Permissions

| Role           | Capabilities                                              |
| -------------- | --------------------------------------------------------- |
| `bank_admin`   | Publish org config, manage all branches/users, review, approve |
| `branch_admin` | Manage branch users, case operations, review, approve     |
| `reviewer`     | Record SOP finding reviews, approve reports               |
| `officer`      | Annotate/correct permitted case data, upload              |
| `auditor`      | Read-only (no write/review actions)                       |

### Scoping

Every query is scoped by **organization** (`user.org`) and **branch**
(`user.branches`). The `authorized(db, Model, id, user)` helper enforces this:
loads the model by ID, checks `model.org == user.org` and
`model.branch_id in user.branches` (or `user.role == "bank_admin"` for
org-wide access). Raises 403 on mismatch.

### Maker-Checker Separation

When `config.payload["maker_checker"]` is `True`:
- The case creator cannot record SOP finding reviews (`case.created_by !=
  user.id` required).
- The case creator cannot approve the final report.

### CSRF Protection

- Session issues a CSRF token via `/api/auth/session` or `/api/auth/login`.
- Frontend stores it in module-level `csrf` variable (`lib/api.ts`).
- Every `POST`/`PUT`/`DELETE` request includes `X-CSRF-Token` header.
- Backend validates the token against the session.

### Concurrency Safety

- **Row-level locks**: `select(…).with_for_update()` on Case, Document,
  CaseContext, DatasetComparison, CaseRun before mutations.
- **Idempotent uploads**: `Idempotency-Key` header → `Batch` table lookup.
  Replayed uploads return the original batch/case IDs.
- **Optimistic concurrency**: DatasetComparison uses `revision` counter —
  mismatch raises 409 ("Comparison changed. Reload before saving.").
- **SOP run fingerprinting**: `case_processing.fingerprint()` detects input
  changes → marks runs `SUPERSEDED` and queues fresh runs.

### Data Sanitization

- `provider_errors.clean()`: Redacts bearer tokens, API keys, URLs from error
  messages before storage/display.
- `provider_errors.api_diagnostic()`: Only allows safe fields (`message`,
  `detail`, `code`, `type`, `loc`, `msg`) from API error responses.

---

## 9. Configuration System

### Versioned Immutable Configs

Each `Config` row is immutable. Publishing creates a new version
(`version = max(version) + 1`). Existing cases pin their `config_id` — they
always run against the config version that was active when they were created.

### Config Payload Structure

```json
{
  "provider": "llama" | "spider-ai" | "fixture",
  "parse_tier": "agentic_plus",
  "extract_tier": "agentic_plus",
  "maker_checker": true,
  "classification_threshold": 0.85,
  "profiles": { "application": {…}, "lld": {…}, … },
  "profile_variants": { "ektp": { "original-v1": {…}, "enhanced-v1": {…} } },
  "templates": { "forex_standard": { "label": "…", "required": […], … } },
  "sop_rules": [ { "id": "…", "operator": "match_exact", "path": "…", … } ],
  "workflow": [ { "action": "upload", "order": 1, … }, … ],
  "customer_aliases": { "PT ABC": "PT ABC Sejahtera" },
  "name_directory": { "bank_names": […], "branch_names": […], … },
  "report_context": { "region_name": "…", "category": "Forex", … },
  "report_mapping": { "DATA_COMPLETION": "DATA_COMPLETION", … },
  "report_title": "Kertas Kerja Forex"
}
```

### Config Data Catalogs (`config_data/`)

Immutable JSON files loaded by `sop.py`:
- `workflow.json` — 9-step workflow definition
- `rules.json` — SOP rule definitions
- `fields.json` — Field catalog
- `scope.json` — Approved scope sources
- `account_opening_rules.json` — Account Opening SOP rules
- `account_opening_sources.json` — Account Opening scope sources
- `enhanced_profiles_v1.json` — Enhanced profile prompt proposals

### Seeding Pipeline

On first startup (`domain.seed()`):
1. Create org `sqe`, admin user, default branches.
2. Build initial config from `sop.defaults()` + engine `profiles.get_profile()`.
3. `Base.metadata.create_all()` creates all tables.
4. `worker_capacity.initialize_slots()` creates 50 WorkerSlot rows.

Additional seeders (run once, idempotent):
- `account_opening_seed.seed_account_opening()` — Adds Account Opening config.
- `spider_config.seed_spider()` — Adds Spider instructions.
- `profile_variants.seed_profile_variants()` — Adds enhanced profile variants.
- `enum_aliases.upgrade_payload()` — Adds enum alias defaults.

All seeders use PostgreSQL advisory locks or SQLite `BEGIN IMMEDIATE` for
cross-instance serialization.


---

## 10. Testing

### Backend Tests (`backend/tests/` — 23 files + `conftest.py`)

`conftest.py` sets up an isolated SQLite environment, inserts `backend/` onto
`sys.path`, imports `app.db.Base` and `app.domain.seed`, and provides fixtures
for sessions, users, and test configs.

| Test file                          | Coverage area                              |
| ---------------------------------- | ------------------------------------------ |
| `test_platform.py`                 | Core API endpoints, auth, case lifecycle   |
| `test_grouping.py`                 | Customer grouping, alias resolution        |
| `test_automation.py`               | SOP rule/automation configuration          |
| `test_transaction_flows.py`        | Transaction flow validation                |
| `test_profile_variants.py`         | Profile variant seeding/comparison         |
| `test_comparison_enhancements.py`  | Dataset comparison enhancements            |
| `test_comparison_fuzzy.py`         | Fuzzy text matching in comparisons         |
| `test_dataset_comparison.py`       | Reference dataset comparison               |
| `test_report_compound_values.py`   | Compound value display in reports          |
| `test_visual_evidence.py`          | Visual evidence crop generation            |
| `test_field_evidence.py`           | Per-field source crops                     |
| `test_parse_evidence.py`           | Parse region → field alias linking         |
| `test_encoding.py`                 | Text encoding handling                     |
| `test_enum_display.py`             | Enum alias display/revalidation            |
| `test_schema_descriptions.py`      | Schema description editing/validation      |
| `test_inbox_pagination.py`         | Inbox pagination                           |
| `test_location_learning.py`        | Location feedback learning                 |
| `test_storage.py`                  | MinIO/local storage abstraction            |
| `test_temporal.py`                 | Temporal workflow integration              |
| `test_spider_provider.py`          | Spider-AI provider                         |
| `test_riplay_platform.py`          | RIPLAY document platform integration       |
| `test_account_opening.py`          | Account Opening SOP/report                 |

**Run:** `cd backend && python -m pytest tests/ -v`

### Engine Tests (`engine/tests/` — 9 files)

163 offline tests using mocked LlamaCloud SDK responses (no API key needed).

| Test file                          | Coverage area                              |
| ---------------------------------- | ------------------------------------------ |
| `test_pipeline.py`                 | End-to-end Parse→Extract pipeline (mocked) |
| `test_batch.py`                    | Batch processing, all 6 suffixes           |
| `test_account_opening_engine.py`   | Account Opening engine profiles            |
| `test_ektp.py`                     | eKTP schema/validation (28 tests)          |
| `test_invoice.py`                  | Invoice schema/validation (26 tests)       |
| `test_lld.py`                      | LLD schema/validation (20 tests)           |
| `test_valas1.py`                   | Valas Declaration 1 (22 tests)             |
| `test_valas2.py`                   | Valas Declaration 2 (23 tests)             |
| `test_riplay.py`                   | RIPLAY schema/validation                   |

**Run:** `cd engine && python -m unittest discover -s tests -v`

### Frontend & Fixtures

No dedicated frontend test runner found; `scripts/browser_smoke.mjs` provides a
Playwright smoke test. `backend/fixtures/` contains 13 JSON files with
synthetic extraction results per document type (used by the `fixture`
provider and tests).


---

## 11. Operations & Tooling

### Operations Scripts (`backend/operations/`)

| Script                | Purpose                                              |
| --------------------- | ---------------------------------------------------- |
| `backup.py`            | Database + storage backup (argparse CLI)             |
| `migrate_003.py`       | Schema migration 003 (adds tables/columns)           |
| `retention_inventory.py` | Retention inventory report for cases/documents     |

### Dev Scripts (`scripts/`)

| Script                | Purpose                                              |
| --------------------- | ---------------------------------------------------- |
| `init_dev.py`          | Initialize dev environment (DB, storage, seed)       |
| `run_dev.py`           | Launch dev servers (API + worker + frontend)         |
| `verify.py`            | Post-deployment verification checks                  |
| `browser_smoke.mjs`    | Playwright browser smoke test                        |

### Migration Utilities (backend root)

| Script                | Purpose                                              |
| --------------------- | ---------------------------------------------------- |
| `generate_templates.py` | Generate PDF/XLSX templates                        |
| `migrate_profiles.py`  | Migrate profile configurations                       |
| `migrate_storage.py`   | Migrate storage keys/objects                         |

### Benchmarks & Templates

- `benchmarks/` — `manifest.json`, `expected-fields.csv`,
  `customer-aliases.example.json` for extraction accuracy benchmarking.
- `templates/` — `forex-kertas-kerja-template.xlsx`,
  `forex-workflow-config-template.xlsx` for user-facing templates.

---

## 12. Key Design Principles

1. **Immutable configurations**: Every config publish creates a new version.
   Existing cases always run against their pinned config — no retroactive
   rule changes.

2. **Frozen case inputs**: SOP runs snapshot all inputs (documents, config,
   context) and fingerprint them. If anything changes, the run is superseded
   and a new one is queued — never silently re-evaluated.

3. **Conservative evidence**: Visual crops come only from explicit provider
   bounding boxes — coordinates are never guessed. Low-confidence extraction
   automatically downgrades SOP findings to `REVIEW`.

4. **Document-only SOP**: SOP rules evaluate extracted document values only.
   No external lookups, no inferred authenticity. Unverifiable rules require
   `REVIEW`, never implicit `PASS`.

5. **Maker-checker separation**: The case creator cannot review findings or
   approve reports when maker-checker is enabled.

6. **Durable checkpointing**: Provider job IDs are saved to
   `Document.provider_state`. Interrupted jobs resume from the last checkpoint
   without duplicate cloud submissions. SDK retries are disabled.

7. **Separation of concerns**: The engine retains full native validation
   behavior; the platform's SOP scope is a separate control layer. Engine
   quality findings are preserved as `technical_findings` — they do not enter
   SOP scores.

8. **No Alembic**: Schema changes use `Base.metadata.create_all()` and
   targeted migration scripts (`migrate_comparison.py`, `migrate_003.py`).
   Run migrations with workers stopped.

9. **Idempotent operations**: Uploads use `Idempotency-Key` headers. Dataset
   comparisons use optimistic revision counters. SOP runs deduplicate by
   fingerprint.

10. **Production guards**: `settings.py` warns on insecure defaults (SQLite in
    production, missing secret key). Temporal runs in dev mode with SQLite —
    not production-durable.


