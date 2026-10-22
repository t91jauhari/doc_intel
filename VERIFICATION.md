# v0.3 verification — 7 October 2026 (Asia/Jakarta)

- Full scoped Python run: 235 tests passed, 81 subtests passed. Temporal test-service module excluded.
- Additional visual-evidence endpoint test passed after the full run; focused evidence suite: 15 tests passed.
- TypeScript and Next.js production build passed.
- Crop checks cover source pixels, rotated pages, invalid units/bounds, missing boxes, storage failures, branch/organization access, reviewed boxes and raw-value preservation.
- RIPLAY pages 1–3, prefix grouping/aliases, assignments and unresolved-crop release gating covered.
- Configuration/Kertas Kerja starter workbooks regenerated successfully.
- Python test run used locally installed runtime dependencies; no fresh installation of every production-pinned dependency was verified.
- Windows fixes, Docker verification, live provider extraction and browser testing were not performed, as instructed.
- Production OIDC/SSO, automated SLA escalation, push events, retention deletion, load tests and actual backup/restore validation remain pending. See docs/RELEASE_0_3.md.
