# Configuration persistence design and implementation status

Step42 implementation: new publications use storage_version 2 and dedicated
configuration_families, configuration_profiles, configuration_profile_variants,
configuration_flows, configuration_report_definitions, configuration_sop_rules
and configuration_generic_sop_rules tables. Each row belongs to an immutable
publication and retains ordered, validated JSON definitions. Seven PostgreSQL
migrations are implemented. Older storage_version 1 publications continue
compiling from configuration_entries without rewriting history.

Nested schemas, prompts and policies remain typed JSON inside their owning
entity; a table for each nested field is unnecessary. Actual SQL names are above
and in store.py; the original conceptual design below uses different names.
Dedicated identity, context, scope and dataset tables remain in use. All 40
historical revisions round-trip exactly through fresh version 2 imports.

Visual/date/money policies, report score groups and signature evidence bindings
are implemented. Evaluator algorithms, authentication and workflow state
transitions remain code-owned capabilities. New business definitions are data;
new algorithms require tested code, never database-supplied executable code.

Earlier implementation record (superseded by these additions):

Current implementation before Step42:
`configuration_publications` and ordered `configuration_entries` preserve family,
profile, flow, rule and report definitions without losing historical extensions.
Dedicated tables store identity policies/bindings, family rule scopes/members and
context definitions. `reference_datasets` stores immutable organization-scoped
reference data. Six explicit PostgreSQL migrations implement these tables and
revision immutability; see MIGRATIONS.md for rehearsals and exact boundaries.

The entity-per-table list below is the original target design. It must not be
read as a list of tables that already exist. Remaining entity normalization and
complex policy contracts are tracked in PLAN.md. The compatibility compiler,
transactional publication, pinned reads and custom-only family catalogs are
implemented. Activation remains a separate release gate.

Use immutable publication revisions, not mutable live rows. Existing Config payloads and case pins remain the compatibility contract during transition.

## Tables
- configuration_publications: organization, revision, schema_version, status, creator, publisher, timestamps, source_config_id, payload_hash; unique organization/revision.
- family_revisions: publication_id, family_key, label, enabled, extraction options, report context.
- profile_revisions: publication_id, profile_key, schema, prompt components, validation policy, schema version.
- family_profile_bindings: publication_id, family_key, profile_key, required flag, ordering.
- identity_bindings: publication_id, profile_key, role, field_path, normalization_policy.
- rule_revisions: publication_id, rule_key, label, evaluator_type, typed policy, scoring policy, source reference, enabled.
- family_rule_bindings: publication_id, family_key, rule_key, applicability.
- dataset_revisions: organization, dataset_key, revision, source digest, storage reference, field bindings.
- report_layout_revisions: publication_id, layout_key, registered renderer, column/group bindings.
- flow_revisions: publication_id, flow_key, family_key, required overrides, rule selections, report/dataset references.

Every dependent configuration row belongs to a publication. Composite keys and foreign keys prevent cross-publication references. Published rows are immutable at the service boundary; database enforcement must be designed and tested before activation. Draft edits create/change draft revisions only.

## Compatibility compiler
Import pinned payload -> normalized draft -> validated immutable publication -> compile legacy payload. First acceptance gate is semantic round-trip equality, including unknown legacy extension properties. Retain source payload during transition so unmodeled keys cannot be silently discarded. Never compile historical cases using latest settings.

## Migration sequence
1. Add new tables only to isolated database using explicit migration.
2. Import all Config revisions, preserving organization and version lineage.
3. Verify deterministic compile and field/rule counts against originals.
4. Shadow-evaluate grouping/SOP on saved results without model calls.
5. Expose configuration service through existing API contract.
6. Activate only after reviewed regression and rollback verification.

## Remaining decisions
The explicit migration runner is implemented. Typed contracts cover the root
envelope, identity, text comparisons, account conditions, field checks, reference
comparison settings, contexts and report projections. Step42 adds visual/date/money contracts and dedicated entity tables. Table normalization
does not eliminate the need for reusable Python evaluators.
