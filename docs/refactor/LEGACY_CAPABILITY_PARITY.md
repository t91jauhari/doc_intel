# Legacy capability parity — local acceptance

Scope: legacy backend capabilities retained by the refactored application, with
Llama provider removal explicitly requested by the user. This is application
compatibility evidence, not a promise of perfect model extraction on every input.

## HTTP contracts

All 65 legacy method/path operations remain present; nine configuration/dataset
operations were added. Dereferenced schemas were compared, ignoring documentation
metadata. Three differences are intentional:

- Config catalog accepts optional case_id to resolve pinned configuration; adds422.
- Spider connector adds typed resource/image/sampling controls, rejects unknown
  properties, and removes hardcoded endpoint/model defaults. Existing explicit
  endpoint/model requests remain supported; settings are persisted configuration.
- Legacy connector writes no longer accept Llama credentials and return410.
  This provider was deliberately removed, including its paid parse/extract flow.

## Capability coverage

| Capability | Regression evidence | Operational evidence |
|---|---|---|
| Login/session, CSRF, origin, roles, branch access | test_platform, test_platform, test_application_architecture | Authenticated browser3100 and API8100 |
| Upload validation, deduplication, grouping, customer labels | test_platform, test_grouping | Synthetic upload/classify completed Step43 |
| Classification/profile/schema selection | test_spider_provider, test_riplay_platform | RIPLAY correctly identified |
| Prompt delivery and field descriptions | test_prompt_delivery | Spider request receipts preserved |
| Provider errors, uncertain submissions, duplicate payment guards | test_spider_provider, test_spider_field_recovery | Original503 preserved without blind retry |
| Field-only rerun, saved patch reuse, manual correction preservation | test_field_reprocessing, test_spatial_grounding | One selected field completed through shared Temporal |
| Profile guidance publication, schemas, document families | test_profile_guidance, test_schema_descriptions, test_document_families | Existing browser configuration acceptance retained |
| Immutable configuration revisions and case pins | test_configuration_store, test_configuration_migrations | Existing case stays pinned atv7 |
| Original media and scoped storage | test_storage | 18 migrated objects SHA verified; original bucket denied |
| Bounding boxes, crops, reviewer location learning | test_field_evidence, test_spatial_grounding, test_location_learning | Source/crop SHA checks and browser refresh |
| Enum display, dates, money, normalization | test_enum_display, test_spider_enum_revalidation; engine suite | No normalization algorithms changed this phase |
| Forex and Account Opening checks, context, score groups | test_forex_sop_v2, test_account_official_rules, test_account_opening, test_generic_sop_runtime | Synthetic incomplete package remains4/43 PASS |
| Visual review, correction audit, findings | test_platform, test_visual_evidence, test_reviewer_quality, test_location_learning | No fabricated visual decisions |
| Report versions, customer/branch layouts and exports | report/platform/storage tests; historical replay | PDF/XLSX/JSON and latest report browser acceptance |
| Reference datasets and comparison policy | test_dataset_registry, test_dataset_comparison, test_dataset_policy | Two private datasets retained |
| Bulk retry, recovery, inbox and assignment | test_platform and workflow/application tests | Historical error retained; completed jobs not replayed |
| Temporal dispatch, activity failure and namespace selection | test_temporal, test_infrastructure_settings | DocumentWorkflow and CaseSOPWorkflow completed in isolated namespace |
| PostgreSQL publication/migration and provider state | test_configuration_migrations, test_provider_state_repository | 11 PostgreSQL tests passed |

Test module families above identify capability evidence; exact collected case
counts and output receipts are recorded in VERIFICATION.md. Unchanged engine,
frontend build and saved-case replay evidence remains valid from Step42.

## Legacy test continuity

236 legacy test functions compared by AST:219 unchanged,10 adapted,7 removed.
The ten retained tests preserve or increase assertion counts. Changes cover typed
contracts/config defaults, explicit seed ownership, handler module boundaries,
and stronger workbook/grouping assertions. Seven removals target Llama-only
parse-job/cache, classification or prompt behavior. Supported Spider replacements
cover cache reuse, classification, uncertain-request guards and complete prompt
delivery in test_spider_provider, test_spider_field_recovery,
test_field_reprocessing and test_prompt_delivery. Llama SDK calls are intentionally
not treated as supported functionality.

## Limits

Complete customer packages have not all been submitted to the live model in this
phase. Backend regression and one synthetic live document validate application
behavior; customer extraction accuracy remains a separate dataset acceptance task.
Remote production deployment awaits the user's server details. SQLite remains a
bounded local preview database; production uses PostgreSQL.
