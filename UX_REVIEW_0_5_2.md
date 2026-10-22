# Evidence and review UX assessment

## Findings and implemented improvements

| Problem observed in the code | Impact | v0.5.2 change |
| --- | --- | --- |
| Comparison shows raw, reference and effective values without their source crops | A matching or fuzzy value can appear more trustworthy than its source supports | Localized source crops beside raw values and in effective correction dialog; original document link and evidence review status |
| Comparison exposes every row equally | Reviewer must search through correct results | Exception view is default; exact matches and non-applicable rows can be restored with one checkbox; fuzzy matches remain visible |
| Transaction flows buried at bottom of Processing defaults | Account Opening configuration is difficult to discover | Dedicated Transaction flows tab, selected by default, with one flow editor at a time |
| Family, reference dataset and report layout independently selectable | Accidental Account Opening/Forex combinations | Family changes select corresponding dataset and report layout; overrides remain under Advanced |
| New flow starts empty without a visible starting-template choice | Requirements and SOP rules must be rebuilt manually | Creation defaults to copying the selected flow and exposes starting-template selection |
| Shared profiles and large prompt editors lack clear scope | User may unknowingly change multiple flows | Required-by flow labels, shared-profile explanation and collapsed advanced prompt editors |
| Inbox displays repeated notifications independently and truncates at 100 | Repeated case navigation; older actions inaccessible | Case grouping within each notification window, overdue first, grouped notification details, mark-read actions and older/newer pagination |

## Evidence semantics

A source crop shows the provider-cited or reviewer-selected source area. It does not independently verify OCR accuracy, semantic field association, a signature's identity or document authenticity. A correct-looking number from the wrong region is still wrong. Compare the crop to both the raw observation and the effective value. Reference sample agreement is not proof of document truth.

Crops use existing field and visual evidence metadata. No region is invented for missing evidence. Composite fields collect descendant leaf crops. Missing coordinates remain explicit; reviewers can select a correct region from the case. Generate/refresh source crops is one action for completed selected documents and makes no new Parse/Extract request. It may rerun local SOP/report processing through the existing API. This patch does not enlarge narrow value-only crops to include surrounding labels.

## What remains to reach the intended UX

1. An actual task queue grouped by case and error cause, with critical field prioritization, assignment and claim/lock behavior. Notifications currently use broad action severity; that is insufficient for risk prioritization.
2. A review session that moves through unresolved fields with keyboard navigation and source context, preserving drafts and showing the next case without repeated navigation.
3. Flow-scoped profile and SOP discovery, plus validated requirement presets when changing an existing flow's family. This patch synchronizes dataset/report layout, but does not silently replace existing document requirements or selected SOP checks.
4. Backend-enforced compatibility between family, dataset and report layout. Advanced overrides are still possible.
5. Carefully scoped bulk resolutions with per-item evidence, current revision checks, reviewer reasons and audit records. This patch only batches notification reading; it never batches approvals or corrections.
6. Measured automatic acceptance policies, evaluated against held-out ground truth. Match, fuzzy match and provider confidence alone must not certify extraction correctness.

Inbox pagination uses 100-notification windows. The same case can occur in multiple windows. Offset pagination is not a fixed snapshot: incoming/resolved notifications may move between windows, so reload while reviewing a changing queue. Reading does not remove pending findings or resolve a case.

## Validation and honest scope

25 backend checks passed (24 existing comparison/evidence tests and one new pagination/isolation/read-semantics test). Frontend production build and TypeScript passed. Browser usability and source-to-crop accuracy on real uploaded samples remain unverified; no accuracy increase is claimed.
