# Account Opening verification — v0.4.0

Validated on 8 October 2026 against the supplied workbook.

- Complete backend/engine suite: **338 tests passed, 81 subtests passed**.
- Post-refactor Account Opening and automation checks: **30 tests passed**.
- Frontend: TypeScript checking and optimized Next.js production build passed.
- New Account Opening runtime modules: Ruff undefined/unused-name checks passed.

Coverage includes all five extraction contracts (180 fields), raw preservation, enum parsing, conditional requirements and unknown controls, identity expiry, configurable business calendars, identifiers with leading zeros, date/time formatting, stamp/signature review, cross-customer discrepancies, NIK/gender correspondence, startup idempotency, migration from seven-profile configuration, custom-flow collision protection, configuration pinning, Excel configuration round trip, dataset isolation, source document access checks, actual PDF crops for seven new visual-field roles, audited new-account-number annotation, dual signing-region review, Account Opening report columns, and mixed exports preserving image bytes and styles.

Fixtures contain synthetic observations, not workbook sample answers. The actual uploaded workbook was read without modification; its unchanged copy and SHA256 appear in the coverage map. The nine field sample columns and ten report examples are not treated as a live extraction result.

No Docker deployment, browser interaction testing or live Llama Parse/Extract execution was performed. Source PDF URLs in the workbook were not downloaded. External CBS/CCTV/specimen checks and physical authenticity are not inferred from OCR. Unsupported BO/survey schema checks and unresolved stamp/business-calendar policies remain REVIEW.

The test runner reports one existing FastAPI/Starlette test-client deprecation warning; it does not affect test results.
