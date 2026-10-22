# Configuration persistence design — proposed, not migrated

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

## Deferred decisions
SQL migration tool and exact JSON policy schemas require dependency inspection. Do not treat this design as implemented. Table normalization does not eliminate the need for reusable Python evaluators.
