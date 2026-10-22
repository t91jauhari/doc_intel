# SQE document platform v0.3 — visual evidence and RIPLAY rules

This is an application-source update based on the saved v0.2.1 package. It does not deploy a stack. Windows fixes, Docker verification, live LlamaCloud extraction and browser testing are excluded from this release's work.

## Delivered

1. RIPLAY checks customer agreement initials separately at the bottom right of pages 1–3. Page 4 supplies the main fields, names/signatures, creation/print dates and stamps. Four physical inspection records are retained, but page 4 has no required footer initial.
2. Platform extraction requests `_visual_evidence` alongside the semantic fields. Native validators receive only semantic values; raw provider output remains unchanged. Evidence must identify the field path, physical page and explicit box coordinates.
3. The worker crops the original PDF into private PNG objects. Observed presence, image availability and review state are separate. A true presence value is preserved even when its crop is unavailable; missing/invalid boxes produce REVIEW and block final report release.
4. Crops appear beside their field observations in the case workspace. Reviewers can open a source page, drag-select a region and save a reason. This queues a new SOP snapshot using stored extraction, without another provider job. An inspected blank region can support an absence finding. A crop cannot prove identity or authenticity.
5. Kertas Kerja PDF includes an evidence section; XLSX includes a Visual Evidence sheet with embedded crops, source hashes, revisions, page and box references. JSON preserves the full evidence records. Old report snapshots retain their evidence objects.
6. Filename grouping recognizes both document-before-customer and customer-before-document labels, including the supplied `(Compressed)Form Riplay-Customer` pattern. Generic Valas labels leave the variant unknown for content classification. Configurable aliases apply only within the organization, branch and upload batch. Existing historical cases are not merged.
7. Settings and workbook General Settings support `customer_aliases`. The supplied example proposes Langit R → Langit Raharja and Sri P → Sri Pujianty. Import/publish these only after confirming their identities. The examples are not silently installed into every organization.
8. `benchmarks/manifest.json` registers six packs / 32 documents with hashes and PDF page counts. `expected-fields.csv` is an editable verified-answer starter; blank values are deliberately not invented ground truth. The original customer ZIPs are not duplicated in the source release.
9. Case owner/deadline controls support authorized branch users. Assignments are audited; the persistent inbox displays due dates and overdue state. Reading remains separate from resolving a case.
10. Case context shows conservative document-derived suggestions. Declaration variants suggest a threshold state; eKTP suggests an individual scenario. Suggestions require explicit acceptance, evidence and a reason through the existing context form. Conflicting declarations are flagged. No inferred direction or payment basis is silently accepted.
11. Operational additions include additive explicit production migration, authenticated organization metrics, an offline database/referenced-object backup utility and a read-only retention inventory. Existing file/count upload limits and saved-provider recovery remain in effect.

## Bounding-box contract

A box uses the original displayed page, including page rotation. Physical page numbers start at 1. Array coordinates are `[x0, y0, x1, y1]`; normalized values range from 0 to 1 with a top-left origin. Never infer units from magnitude. Metadata adapters can also supply explicit PDF-point boxes or pixel boxes with source width/height. Missing page, reversed/empty rectangles, non-finite values, mismatched pages or out-of-bounds boxes are rejected.

Example platform provider result:

```json
{
  "extract_result": {
    "customer_signature": {"present": true, "page_number": 4},
    "_visual_evidence": [
      {"field": "customer_signature", "page_number": 4,
       "bbox": [0.55, 0.68, 0.87, 0.82], "units": "normalized"}
    ]
  }
}
```

This is a contract illustration, not an extraction result for any supplied customer. Other required semantic properties must also be present. The crop pipeline supports signatures, initials, stamps, meterai, photos/portraits and approval fields. New image-bearing fields must be registered explicitly if their names do not match these categories.

Provider boxes are observations rather than proven localization. Live provider accuracy remains untested by instruction. Review the crop against its source page when uncertain. Unknown metadata shapes remain REVIEW rather than being guessed.

## API additions

- `GET /api/documents/{id}/pages/{page}`: authorized rendered source page.
- `GET /api/documents/{id}/evidence/{revision}/{image_id}`: authorized current evidence crop; stale revisions return 404. Historical report downloads carry their frozen embedded evidence.
- `POST /api/documents/{id}/visual-box`: reviewer-only selection with field, page_number, normalized bbox and reason; records an audit event and queues SOP.
- `GET /api/cases/{id}/assignment`: owner/deadline and authorized candidate list.
- `PUT /api/cases/{id}/assignment`: reviewer/admin assignment; rejects users outside the organization/branch.
- `GET /api/operations/metrics`: bank-admin-only queue/state counts and overdue assignments, scoped to the organization.

## Upgrade and operations

Preserve `.env`, database and MinIO contents. Stop API/workers before the explicit production migration:

```bash
cd backend
python operations/migrate_003.py
```

The migration adds tables without dropping existing rows and publishes a new RIPLAY configuration version. Existing cases keep their original configuration IDs. Custom prompts are retained with an appended authoritative page-rule clarification. Development startup still initializes its schema; production startup does not run `create_all` automatically.

Historical policies without `required_initial_pages` retain their former page set. Use a new case under the new configuration for the revised rules. Historical reports are not rewritten.

With API/workers stopped, back up the database and all referenced originals, current/historical crops and report objects:

```bash
python operations/backup.py --destination /secure/backups/sqe-run
```

The destination must be new. PostgreSQL requires `pg_dump`; SQLite uses its backup API. The utility copies referenced object bytes and a hash manifest with restrictive local permissions. It does not include infrastructure secrets or unreferenced orphan objects. Isolated restore validation and infrastructure snapshot configuration remain required before production reliance.

Read-only retention review, using a bank-approved period:

```bash
python operations/retention_inventory.py --organization sqe --days 3650
```

The number is an example, not an approved retention policy. The utility never deletes. Legal holds and purge authorization need bank policy before a deletion mechanism can be enabled.

## TODO sequence and remaining inputs

| Step | Status | Remaining work/input |
|---|---|---|
| RIPLAY page rules | Implemented | Ground-truth verification using supplied cases |
| Crop evidence and private access | Implemented | Live localization accuracy intentionally deferred |
| Evidence workspace and audited region selection | Implemented | Browser testing intentionally deferred |
| SOP/report evidence | Implemented | Bank-approved visual examples |
| Benchmark preparation | Inventory and starter template ready | Verified fields, expected classification/SOP results and scenarios |
| Grouping aliases | Implemented | Confirm aliases; define transaction reference convention for repeat customers |
| Scenario/SOP policy | Existing editor/template retained | Required-document matrix; invoice date/due date; party mapping; partial/progress payment basis |
| Case-context automation | Conservative suggestions implemented | Approved source-to-context policies before automatic acceptance |
| Review cockpit | Crops, assignment, due dates implemented | Push/SSE events and automatic SLA escalation remain unimplemented; polling remains |
| Production controls | Metrics, additive migration, backup and retention inventory added | Enterprise SSO adapter/provider setup, automated backup scheduling/restore verification, approved retention purge, production load/tenant-isolation validation remain pending |
| Documentation/package | Updated | Excluded verification stays excluded |

SOP scope remains YES-marked controls plus SOP3, with external verification and CCTV excluded. Existing finality policy allows reviewed FAIL reports but blocks unresolved findings and required missing crops. Business policy choices are not filled with guesses.
