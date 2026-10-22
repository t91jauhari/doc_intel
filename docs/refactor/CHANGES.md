# Per-step change inventory

## Step 1 — configuration persistence
Commit: 6df69b6 — feat(configuration): add lossless versioned publication store and offline compatibility verification.
Created: backend/app/configuration/__init__.py, store.py, verify_snapshot.py, README.md; backend/tests/test_configuration_store.py.
Modified: docs/refactor/CHECKPOINT.md, DECISIONS.md, VERIFICATION.md.
Evidence: 10 storage tests; selected regression 79 passed; 40 snapshot round trips match.

## Step 2 — PostgreSQL migration
Commit message: Add transactional configuration migrations and PostgreSQL compatibility checks.
Created: backend/app/configuration/migrate.py; backend/app/configuration/migrations/0001_publications.sql; backend/app/configuration/verify_postgres.py; backend/tests/test_configuration_migrations.py; docs/refactor/CHANGES.md.
Modified: backend/app/configuration/README.md; docs/refactor/CHECKPOINT.md; docs/refactor/MIGRATIONS.md; docs/refactor/VERIFICATION.md.
Evidence: 13 tests passed; final rollback assertion rerun 3 passed. All 40 historical revisions reconstructed twice in isolated PostgreSQL; original rows unchanged. No live migration or activation.
Git log provides the authoritative commit hash for this step.
