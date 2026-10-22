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

## Step 3 — configurable identity policy
Commit message: Make customer identity checks configurable by profile and field.
Created: backend/app/configuration/identity.py (typed contracts, schema binding validation, pure matching); backend/tests/test_identity_policy.py (19 policy tests); docs/refactor/IDENTITY_CONFIGURATION.md (configuration and compatibility limits).
Modified: backend/app/grouping.py (explicit policy path with historical fallback); backend/app/domain.py (publish validation); backend/tests/test_configuration_store.py (policy round trip); docs/refactor/CHECKPOINT.md; docs/refactor/CHANGES.md; docs/refactor/VERIFICATION.md.
Verification: 42 tests passed with one baseline failure deselected; added persistence test passed separately. Failure reproduced in untouched baseline worktree, not caused by new identity policy. No live deployment.
