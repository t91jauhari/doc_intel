# Refactor recovery checkpoint

Status: BASELINE_IN_PROGRESS. Refactor is not activated.

Live application: work/sourcecode/document-platform; ports 3000/8000. Do not edit or redeploy it for refactor work.
Isolated implementation: work/refactor/document-platform. No live .env copied. No model calls authorized by this checkpoint alone.

## Resume procedure
1. Read this file, PLAN.md, INVENTORY.csv and VERIFICATION.md.
2. Inspect git status and log in isolated implementation; reconcile uncommitted changes.
3. Inspect running commands and Docker services before repeating any operation.
4. Check migration ledger before database writes. Never point isolated tests at the live database.
5. Continue the next incomplete item and update this checkpoint after verification.

## Current operation
Baseline copy and PostgreSQL custom-format dump initiated. Verify completion and archive readability before marking complete.

## Next action
Create baseline commit, record hashes and live health. Design normalized configuration revision tables and compatibility compiler without changing existing case pins.

## User requirements
Keep current application operational. Database-backed business configuration; reusable algorithms stay in code. Preserve administrator settings and historical reproducibility. Compare old/new behavior before activation. No silent startup overwrite. Reversible cutover.
