# SQE development and verification — v0.2.1

## Windows decoding fix

The reported error was reproduced against backend/app/config_data/scope.json: byte 0x9D at offset 12675 is part of a UTF-8 closing quotation mark. Windows CP1252 cannot decode that byte. The SOP catalog reader used the operating system default encoding, and the catalog is consulted by many configuration and processing actions.

Production readers now explicitly use UTF-8 for the SOP catalogs, extraction policies, approved name directory and synthetic fixtures. The launcher also supplies UTF-8 settings to child processes for console output. The file fix works independently of those settings. Do not change valid UTF-8 catalogs into ANSI or suppress decoding errors: that would corrupt rule text.

Three regression tests cover the exact failure, all catalogs/profiles under an emulated CP1252 default, and API configuration/export/upload/worker/report actions under that default. This is a Windows-locale simulation on Linux, not a claim that the Windows launcher was executed.

## Upgrade an existing installation

1. Stop the API, worker and frontend.
2. Copy the v0.2.1 source files over the existing project, retaining its .env and data directory. The ZIP excludes both. Retain the existing credentials, database, uploaded originals and report objects.
3. Start with start.bat or start.sh. Restart API and workers together so both load the corrected readers. For Compose, rebuild the application services.
4. Reopen Configuration and the case workspace. Retry failed document/case jobs through the existing recovery controls. Existing provider checkpoints are retained; uncertain paid submissions still require reconciliation and are not automatically recreated.

No database schema migration is introduced by this patch.

## Automatic development style

During an active development session, the implementation loop is:

1. Take the next approved task and record its acceptance criteria.
2. Inspect the affected code and policies; distinguish implementation work from an unresolved bank decision.
3. Implement the change and add regression checks when needed.
4. Run the relevant checks, fix failures and rerun the affected checks.
5. Run the release gate below. It starts an actual headless Chromium browser against isolated running API, worker and production frontend services.
6. Inspect stored case results and exported artifacts. Record screenshots, logs, status and skipped checks.
7. Update documentation and produce the release package; proceed to the next independent approved task.

This release provides an automated verification runner. It does not install a self-modifying background coding agent or an unattended deployment bot. An active assistant session can perform approved coding work without repeated permission requests. It cannot invent bank policies, unavailable documents or provider credentials. Publishing this local release does not deploy it to the bank's production environment.

## One-command verification

Install dependencies using the normal development launcher first. Install the browser once from frontend/: npx playwright install chromium. Stop any existing development API/frontend on ports 8000/3000 before running the isolated browser check.

From the project root on Windows:

    .venv\Scripts\python.exe scripts\verify.py

From the project root on Linux/WSL:

    .venv/bin/python scripts/verify.py

The gate runs backend tests, engine tests, TypeScript checking, the production frontend build and the browser smoke test in order. A failed check stops the gate with a nonzero exit code. Logs and result.json are saved beneath data/verification/<UTC timestamp>/. --skip-browser explicitly records that the browser was not run and is not a complete release verification.

Browser evidence includes desktop/mobile screenshots, saved PDF and XLSX reports, JSON report snapshots, case results and service logs. All seven document profiles are exercised across two customer groups. The test checks that documents complete, reports persist, a context change creates another report version, the PDF has a valid file signature, and the branch workbook has its required sheets, two customer rows and numeric/blank SOP scores. Browser exceptions and HTTP 5xx responses fail the test.

Fixture mode is deliberately synthetic: uploaded PDFs are not OCR-extracted. Passing this gate demonstrates application wiring and report behavior, not Llama extraction accuracy. Live provider validation must use approved PDFs and a configured key; real MinIO/PostgreSQL deployment, native Windows execution and production load testing remain separate checks.

## Approved task queue and dependencies

| Work | State / dependency |
| --- | --- |
| Correct the reported Windows decoding issue | Completed in v0.2.1 |
| Repeatable automated release verification with browser/artifact evidence | Completed in v0.2.1 |
| Complete SOP policy rules | Requires invoice-date/due-date, party ownership, payment-basis and stamp policy decisions |
| Real-document extraction benchmark | Requires approved customer packs, ground truth and configured Llama credentials |
| Automatic case context and transaction grouping refinements | Requires a transaction discriminator and approved document-to-context mappings |
| Review cockpit and inbox assignment/SLA improvements | Implementation backlog; acceptance criteria should define reviewer ownership and escalation |
| Production hardening | Implementation backlog; deployment target, SSO, volumes and retention determine the infrastructure work |

Already decided: Temporal, MinIO, filename-based customer grouping followed by classification, seven supported document types, eligible YES SOP scope plus SOP3, exclusion of external verification/CCTV, and CSV outputs separated by document type. These do not need another approval.
