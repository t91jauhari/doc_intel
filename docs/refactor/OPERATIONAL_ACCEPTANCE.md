# Operational preview acceptance — 23 October 2026

The preview on3100 now processes uploads using the refactored backend on8100.
API and worker run the accepted step42image with persistent isolated DB/files.
Existing private reference datasets are registered separately from public source.
The approved provider connection is encrypted in the preview database; the user
selected pct-prod-spider/pecut/gemini-3.8-flash-high. Original app3000 is unchanged.

Live browser test:one explicitly synthetic RIPLAY PDF; grouped and uploaded;
classification/extraction200;documentCOMPLETED with10fields. Five expected text
values matched; signature absence correct; five source crops decoded. SOP ran
43checks and generated latest reportv2. PDF/XLSX/JSON exports parse and include
customer label in filenames. Review page has0pending decisions and0overrides.

The synthetic case intentionally lacks required Forex documents/signatures, so
WAITING_DOCUMENTS/FAIL (4/43points) is correct. Processing completion is separate
from compliance PASS. One Argon503 was preserved; after the user-selected model
change, two successful submissions completed the same document. Three provider
submissions total, with no automatic paid replay after restart.

Persistence verified by restarting both API and worker after completion. The
original upload hash,10fields,2report versions,2reference datasets and completed
job remained. Obsolete stopped preview container removed after verified backup;
current volume, private env and recovery files retained outside Git.

Synthetic case:628f0b46-b29c-441a-afd4-c7b83bbb66dd.
Latest report:146ed0f6-c3c2-4361-91bb-01d85955410c.
API:sqe-refactor-operational-api-1;worker:sqe-refactor-operational-worker-1.
Volume:sqe-refactor-operational_preview-state. Runbook:OPERATIONAL_PREVIEW.md.

Created/changed files this phase:compose.preview.yaml;
scripts/export_public_source.py;docs/refactor/OPERATIONAL_PREVIEW.md,
OPERATIONAL_ACCEPTANCE.md,PLAN.md,CHECKPOINT.md,CHANGES.md,VERIFICATION.md.
Private activation helper/backups/credentials/syntheticPDF/screenshots are excluded.
Six source-export guards and compose validation passed; no backend algorithm or
frontend source changed, so prior full code acceptance remains applicable.

Follow-up observation:crop list also shows three internal.complete metadata rows
without images. The five actual text crops exist. Full real-customer package UAT
and server-specific deployment are separate from this synthetic acceptance.

Publication verified:public mainc1e41c465ecc7d5a6582cb5102021e15a3bea79e.
Sourcee4a83e4;356export files;0scanner blockers;hashes and6guards passed.
Runtime source hashes match accepted Step42. Screenshot retained privately.
