# Field extraction and profile editing

The platform now supports re-extracting selected fields from an existing document without replacing the rest of its extraction. Saved field descriptions and profile instructions are sent to Spider-AI. Previously only field names were sent, so changing a description did not affect that provider.

## Reviewer workflow

1. In Configuration → Document profiles, select the document profile. Search field instructions by field key or displayed field label. Edit the relevant extraction description and publish the configuration.
2. To add a field, enter its key, display label and extraction instruction under Profile fields and schema. The advanced editor supports existing schema/type and label changes. Every property must have a display column.
3. In a case, select the document and expand Reprocess selected fields. Select the fields, enter a reason and optional one-off extraction guidance, and choose whether to use the latest published profile.
4. The worker reads the original physical pages for those fields. Untouched raw and effective values remain unchanged. A new case evaluation/report is queued using the existing workflow.
5. Recent field reprocessing shows request status and configuration version. A failed request can be resumed. Cached successful provider pages and saved extraction results are reused.

Reviewer corrections are preserved by default. Replacing corrections requires the explicit checkbox; previous corrections are retained in the request history. A failed extraction never removes those corrections or replaces the original values.

## Profile scope

Spider-AI supports edits to existing field structures. Native LlamaCloud/fixture providers support additional profile fields and description edits; their registered core field types remain constrained by the existing validators. Added native fields are checked separately and included in the effective result. Renaming a field used by an SOP rule still requires updating that rule deliberately.

The quality release adds eight invoice fields: Ship To Name, Ship To Address, Ship To Phone, Discount, Subtotal Less Discount, Shipping/Handling, Beneficiary Name and Address Bank. Valas 1 gains Stamp verification. CSV exports include configured and historical business fields, excluding internal page results.

## API

`POST /api/documents/{document_id}/reprocess-fields`

```json
{
  "fields": ["swift_code"],
  "instruction": "Read the code from its own labelled field, character by character.",
  "reason": "Reinspect an uncertain code",
  "use_latest_config": true,
  "replace_overrides": false
}
```

The response contains `job_id`, `request_id`, selected fields and configuration version. History is available at `GET` on the same path. A failed request can be resumed at `POST /api/documents/{document_id}/reprocess-fields/{request_id}/retry`.

For an uncertain provider submission, retry requires an explicit body `{"accept_possible_duplicate_charge": true}`. This applies only to a pending stage belonging to that request. Completed cached pages are retained. Unknown or unrelated pending submissions remain blocked.

Permissions, branch/organization access, CSRF checks and configuration publication permissions follow the existing application rules. Active document jobs prevent overlapping field requests. Before applying results, the worker checks that source values and reviewer corrections have not changed concurrently.

## Validation utilities

- `scripts/validation_inventory.py`: reads invalid rows from the comparison workbook and resolves each to a profile key. It generates the instruction target catalog without copying expected customer answers into prompts.
- `scripts/run_field_regression.py`: reprocesses the targeted fields on stored documents, with at most two concurrent document requests. This uses the configured provider and can incur provider charges.
- `scripts/resume_field_failures.py`: explicitly retries HTTP 503 failures once; requires its acknowledgement flag.
- `scripts/export_field_regression.py`: exports final results from durable request records. Counts cover previously invalid rows only, not whole-dataset accuracy.
- `scripts/check_stored_field_integrity.py`: compares untouched values with a pre-run database baseline.
- `scripts/field_ui_smoke.mjs`: checks profile-field drafting and the field selector without queuing extraction. It uses an existing completed case; `FIELD_UI_CASE_ID` can select one explicitly.

Reference data stays outside provider prompts. If a visible document conflicts with the workbook, preserve the document observation and flag the reference for review. For example, the Sri P signing block visibly contains names that the validation workbook labels blank.

## Verification and operational limits

The implementation was checked with isolated Docker backend tests, a production frontend build, browser interaction checks and real stored-document extraction. Every one of the 29 affected documents passed a comparison of untouched raw/effective values with the pre-change database backup. All three failed provider requests retained their original values.

Three document requests still returned HTTP 503 after one controlled retry. Their field histories remain failed and resumable; no further automatic retries were issued. The remaining reference differences are visible in the exported CSV, including confirmed reference inconsistencies. Native LlamaCloud field reprocessing was checked with fixtures and mocked SDK paths; live extraction in this environment used the configured Spider-AI provider.
