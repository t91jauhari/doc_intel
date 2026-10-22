# Annotated field remediation

The 40-row reviewer workbook is the scope of this run. The review notes were preserved before changes. No customer/sample expected answers were included in extraction prompts.

## Changes

- Field guidance now distinguishes RIPLAY autographs from separate entries on the parenthesized name line. It covers complete recipient/bank panels, handwritten transaction descriptions and charges, local relationship selections, and the lower bank-approval signature area.
- Invoice guidance accepts equivalent labels such as SOLD TO and DESTINATION. Single-item monetary roles are explicitly defined, inherited currency uses an explicit invoice code, and a grand-total delivery heading is distinguished from a separate freight charge.
- Selected-field rereads include enlarged crops of the original application/LLD regions alongside the full physical page. Original page content remains the evidence. The crops contain no reference-answer overlay.
- Combined display now includes a stored charge amount and an Other description instead of showing only selected labels. The frontend and report/export presentation use the same rule.
- Regression comparison checks the payment method and amount together, preserves identifier digits, accepts reordered bank/branch components only when all words match, and distinguishes monetary grouping from decimal precision. Different amounts remain invalid.
- Configuration seeding uses a fixed system actor within the existing database column limit; the release identifier remains in the configuration and audit metadata.

## Reference handling

The reviewer explicitly accepted 12 existing extracted values. These are reference corrections, not newly recovered extraction values. The original Steve invoice bank block additionally confirms Foshan rather than Fushan. The enlarged Poko application confirms 4th rather than P4th and the continuation 91731 Pasadena, USA; its combined reference now includes the full visible address requested by the reviewer. Original references remain in the result CSV and previous workbook copy. Case reference edits use the existing revision-checked, audited comparison API. The amount-only dataset fee row remains distinct from the combined method/fee review field.

Bayu's declaration address remained misspelled after rereading. The reviewer explicitly requested a same-customer fallback in that situation. An audited effective correction copied the verified payer address from the same case's LLD, preserving the declaration's raw extraction. This is identified separately from model-only extraction.

## Validation and scope

All 40 annotated rows now compare valid against the reviewed references, with zero invalid rows. The resolution breakdown is 22 re-extraction fixes, one re-extraction plus a document-verified reference correction, 13 reference-only corrections, two combined-display/comparison fixes, and two audited reviewer corrections. All 18 provider requests completed without provider errors. Untouched raw and effective values were compared with a pre-run snapshot for all 19 affected documents; all checks passed. Sixteen focused backend tests passed, including selected-field integrity, cache reuse, permissions, prompt idempotence, enlarged original crops and complete-value comparison. Eleven browser workflow checks passed without browser errors. Production backend/frontend Docker images are built and deployed locally.

Poko's LLD postal code and bank signature were recovered by the enlarged reread. The remaining leading-unit ambiguity was resolved by the user's explicit confirmation, “Use Al (letter L), as in the reference.” An audited effective correction changed only that character; the model's raw A1 observation remains preserved. Earlier unannotated provider-error rows outside this 40-row sheet are not included in these counts. This run is not a claim of whole-dataset or model-only 100% accuracy.
