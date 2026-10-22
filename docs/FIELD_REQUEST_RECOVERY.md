# Field-request recovery after gateway timeouts

The Sri P case (`2c9a2036-8606-40a4-9b3d-0d3b21867d2f`) retained its original extraction, but its six-field reread failed. The saved Spider response was HTTP 503 with an upstream `[502]: fetch connect timeout (reset after 30s)` message. This identifies a gateway-to-model connection timeout rather than a document parsing error or evidence of invalid API credentials.

The application kept the submission marked uncertain and restored the document to COMPLETED so the earlier extraction remained available. The case recovery panel then offered whole-document resubmission, whose endpoint rejected both the field-stage identifier and the document's COMPLETED status. Field-specific recovery existed in a collapsed history panel. A direct `#recovery` link could also select a different document and hide the relevant error.

The fix adds an inline **Retry field extraction** action, opens the failed request history, and selects the errored document when opening the recovery link. Whole-document resubmission and unrelated provider-job reconciliation are hidden for field failures. The endpoint returns actionable field-recovery directions to older clients.

The adapter recognizes only the gateway's explicit structured pre-connection failure as a confirmed rejection. Future such failures clear the pending marker and show a connection-specific error. Legacy cases are reconciled on an explicit retry only after checking that the stored response's stage and request ID match the exact pending submission. Generic 5xx responses, read timeouts and missing/mismatched evidence remain uncertain and require duplicate-charge acknowledgment. No automatic paid retries were added.

Field retry retains the original request and its captured configuration; completed page responses can be reused. Existing raw values, unselected effective values and reviewer corrections remain protected. The recovery is audited, including whether the saved evidence established a pre-connection rejection.

Verification: six focused recovery tests passed, along with 33 existing provider/field/prompt-delivery tests. Five browser checks passed with intercepted submissions and no browser errors. Production API, worker and frontend builds succeeded and the updated services were started locally. A separate live recovery receipt records the actual case outcome and field-integrity checks.

## Live case outcome

One explicit retry of field request `b17a08b4-4ebb-4f33-a7b4-3d3ce30b2992` was accepted without duplicate-charge acknowledgment. Job `88b4ed10-27ce-4ef9-9a14-58193608a10c` reached the provider and again received the gateway-to-model connection timeout. This is still an upstream availability problem; the extraction did not complete successfully.

The failed submission is no longer stuck: `pending_create` is null, the history reports `can_retry=true` and `requires_duplicate_charge_ack=false`, and the case shows **Retry field extraction**. The browser verification passed again against this state. Independent checks confirmed that all raw values, all effective values and every reviewer correction are unchanged. No further live retries were started. The Spider gateway's connection to its configured upstream model must be restored before this reread can succeed.
