# UX Remediation Implementation Plan

**Scope:** Frontend-only fixes for state communication and contextual action hierarchy issues identified in the UX audit (15 Oct 2026).
**Constraint:** No backend/API changes except Step 6. No behavioral changes to workflows — presentation and affordances only.

---

## 1. Audit Summary (evidence base)

Live-tested as `sqe@bic.local` (Bank Admin) on `localhost:3000`, Chrome 1440px.

### Findings — State Communication
| # | Finding | Where observed |
|---|---|---|
| S1 | 4 inconsistent status vocabularies for the same state (Title Case, lowercase raw, blank cells, duplicated badges) | Cases list, case header, filter dropdown |
| S2 | Internal variable leakage in SOP panel (`total a: 0`, `total b: Review`, snapshot hash as label) | Case detail SOP panel |
| S3 | Error diagnosis requires domain knowledge; no transient-failure batching guidance; no first-line cause | Error document expansion |
| S4 | Case detail page is a ~4,000-word single scroll with no section navigation | Case detail |
| S5 | Inbox renders 23 near-identical rows; same customer repeated; no urgency differentiation | Inbox |
| S6 | Missing-doc info hidden behind navigation; redundant customer name repetition | Overview/Cases tables |
| S7 | Undefined terminology ("Kertas kerja", "Revalidate eKTP spelling aliases") | Nav, case detail |
| S8 | Filter dropdown mixes lifecycle states with SOP results | Cases list |
| S9 | No visible processing activity feed | Overview |
| S10 | Timestamps without year or relative context ("15 Oct, 10:20") | All tables |

### Findings — Contextual Buttons
Measured fill-states (solid background) per view vs. healthy maximum (~2):
| Page | Filled count | Verdict |
|---|---|---|
| Upload | 2 | ✅ reference implementation |
| Overview | 2 (competing primaries) | ⚠️ |
| Cases | 0 (no primary at all) | ⚠️ |
| Case detail (collapsed) | 6 | ❌ |
| Case detail (expanded error doc) | 5–6, no recovery ranking | ❌ |
| Inbox rows | 2 per row × 23 rows, 10px font | ❌ |
| Settings | 4, "Publish" beside "Test" at equal weight | ❌ dangerous |

Specific misplacements: "Revalidate eKTP spelling aliases" (widest filled button on case page, technical utility), "Mark displayed notifications read" (bulk action filled at top), "Review batch grouping" vs "Repair customer grouping" (duplicate-looking pair), "Save assignment" (21px tall), row actions 10px font on Inbox.

---

## 2. Implementation Plan

### Step 1 — Canonical status taxonomy and shared status component
**Goal:** One status vocabulary rendered identically everywhere; no blank status cells.
**Files:** new `frontend/lib/status.ts`; new `frontend/components/status.tsx`; `frontend/app/cases/page.tsx`; `frontend/app/page.tsx`; `frontend/app/cases/[id]/page.tsx`.

1.1 Create `frontend/lib/status.ts` with a single mapping:
```ts
export const STATUS_LABELS: Record<string, { label: string; tone: "neutral"|"info"|"warn"|"error"|"ok" }> = {
  queued:            { label: "Queued",            tone: "neutral" },
  processing:        { label: "Processing",        tone: "info" },
  waiting_documents: { label: "Waiting Documents", tone: "warn" },
  processing_error:  { label: "Processing Error",  tone: "error" },
  needs_review:      { label: "Needs Review",      tone: "warn" },
  ready:             { label: "Ready",             tone: "info" },
  finalized:         { label: "Finalized",         tone: "ok" },
};
export const SOP_LABELS = { ok: "Pass", review: "Needs Review", fail: "Fail", none: "Not run" };
export function statusMeta(key: string) { return STATUS_LABELS[key] ?? { label: key || "—", tone: "neutral" }; }
```
1.2 Create `frontend/components/status.tsx` exporting `<StatusBadge value tone />` (single size, tone colors) and `<SopBadge value />` which renders `"Not run"` instead of blank.
1.3 Replace all inline status rendering in cases list, overview recent-cases table, and case header with `<StatusBadge>`. Case header shows ONE badge (drop the duplicated `Processing Error` + `Error` pair).
1.4 Cases table: never render an empty workflow/SOP cell — always render the badge, using `none → "Not run"`.
**Accept:** grep for raw state strings in list pages returns only `status.ts`; no empty status cells in any table.


### Step 2 — Split the workflow-state filter (S8)
**File:** `frontend/app/cases/page.tsx`.
2.1 Replace the single "All workflow states" select with two selects: **Status** (lifecycle states from `STATUS_LABELS` only) and **SOP result** (Pass / Needs Review / Fail / Not run).
2.2 Map the old `unresolved_checks` value to the SOP filter's `Needs Review + Fail` composite (client-side OR filter, no API change).
**Accept:** dropdown options contain no mixed-concept entries; both filters combine.

### Step 3 — Humanize the SOP workflow panel (S2)
**File:** `frontend/components/case-sop.tsx` (or the case-detail section rendering `DATA COMPLETION` / `total a`).
3.1 Replace `DATA COMPLETION: 0`, `total a`, `total b`, `total` with a summary line: `"Passed 1 of 4 checks · 3 need review"` and per-check rows using `SOP_LABELS`.
3.2 Render the snapshot hash as `Complete · <time>` with the hash in a `title` attribute.
**Accept:** no strings matching /total [ab]/ visible in DOM.

### Step 4 — Action hierarchy system (biggest change)
**Goal:** One filled primary per view/row; consistent sizes.
**Files:** `frontend/components/ui.tsx` (button variants), then per-page call sites.

4.1 In `ui.tsx`, formalize 4 variants: `primary` (filled), `secondary` (ghost/outline), `tertiary` (text link), `danger` (outline-red). Enforce min height 32px, font 12px floor (bump Inbox's 10px rows).
4.2 Apply demotions (filled → secondary):
   - Inbox: "Mark case notifications read" (per-row) and "Mark displayed notifications read" (behind "…" overflow or with `confirm()`).
   - Case detail: "Revalidate eKTP spelling aliases" (also relocate into Classification/provider checkpoints section), "Review batch grouping", "Compare effective values with dataset sample".
   - Settings: "Archive" (→ `danger` outline), "Duplicate".
4.3 Overview: make "Open inbox" the filled primary of the "Your next action" panel; keep "New upload" filled in header (allowed: one primary per *region*).
4.4 Cases page: add a filled "Upload documents" button top-right (primary for the page).
4.5 Bump small targets: "View all", "Open PDF", "Move to another case", "Save assignment" → ≥32px height.
**Accept:** ≤2 primary actions per view/region (ideally 1); no action < 32px tall.

### Step 5 — Recovery-action ranking on failed documents (S3)
**File:** `frontend/app/cases/[id]/page.tsx` (error document expansion).
5.1 Group the three recovery controls into a labeled block:
```
Next step (recommended):  [Confirm document type]     ← filled primary
Advanced recovery ────────────────────────────────
  [Retry] (when pending_create is null) · [Resubmit Spider-AI request — may incur charge] (ghost) · [Reconcile provider job] (ghost)
```
5.2 One-line first cause from `provider_state`: if `pending_create` is set, show `Network request interrupted — the request may have reached the provider. Details` with an expandable showing request ID, stage, timestamp from `spider_request_details`.
5.3 Move the consequence warning under the Resubmit button (contextual) instead of a paragraph above all three.
**Accept:** exactly one filled action in the recovery block; "may incur charge" adjacent to Resubmit only.

### Step 6 — Batch failure guidance (S3 extension; only backend touch)
**Files:** `backend/app/main.py` (one new GET route), Overview/Cases banner component.
6.1 Backend: `GET /api/documents/failure-summary?since=<ts>` returning grouped counts `[{error_prefix, count, case_ids, first_seen}]` from `documents.error` prefix grouping. Read-only, auth-scoped.
6.2 Frontend: when ≥3 documents share an error prefix within 24h, show a dismissible Overview banner: `"6 documents failed with the same network error since 10:28 — likely a temporary outage. Review affected cases"`.
**Accept:** banner appears for the current 9-document network-error cluster; endpoint requires auth; add test in `backend/tests/`.

### Step 7 — Inbox density and grouping (S5)
**File:** inbox page.
7.1 Group rows by customer: summary row `"Poko — 3 cases: 2 review findings, 1 processing error"`, expandable to individual notifications.
7.2 Urgency visual: error-toned/overdue rows get a colored left border + icon; keep overdue-first ordering.
7.3 Exactly one filled action per group: "Review case" (primary). "View notifications together" → tertiary link.
**Accept:** no customer appears as more than one top-level row.

### Step 8 — Case detail section navigation (S4)
**File:** `frontend/app/cases/[id]/page.tsx`.
8.1 Sticky in-page tabs at the top of the case body: `Overview · Documents · Fields · SOP · Reports` (anchor-scroll, not routing — no data refactor).
8.2 Keep all sections rendered (progressive disclosure via scroll); tabs highlight the in-view section (IntersectionObserver).
8.3 Document list lives under "Documents", expanded by default; the 90-row field table collapses behind the "Fields" tab anchor.
**Accept:** page renders fully without JS tab state; each tab lands within one viewport of its section.

### Step 9 — Table content density (S6, S10)
**Files:** `frontend/app/page.tsx`, `frontend/app/cases/page.tsx`; new `frontend/lib/time.ts`.
9.1 Missing-document chips in the progress column: `"2/5 · Missing: Invoice, Riplay"` (data already present as required-vs-completed doc types).
9.2 Drop the repeated customer name in the second line of CUSTOMER/CASE cells (keep `customer / short-id` once).
9.3 `frontend/lib/time.ts` with `formatWhen(ts)`: relative (<7d: "4 min ago"), else "15 Oct 2026, 10:20"; apply to all table timestamps with `title` = full ISO.
**Accept:** no timestamp without relative-or-year context; progress column shows missing doc names when incomplete.

### Step 10 — Terminology glosses (S7)
**Files:** `frontend/components/shell.tsx`, case detail.
10.1 Nav item `Kertas kerja` gets `title="Work paper report"`; same gloss inline at first use on the case page.
10.2 Relocated "Revalidate eKTP spelling aliases" (per 4.2) relabeled "Re-run alias validation (provider tool)".
**Accept:** every non-English/domain term has a title attribute or inline gloss at first use.

---

## 3. Sequencing & Effort

| Step | Depends on | Effort | Risk |
|---|---|---|---|
| 1 (status system) | — | M | Low |
| 2 (filter split) | 1 | S | Low |
| 3 (SOP labels) | 1 | S | Low |
| 4 (button system) | — | M | Medium (touch many files) |
| 5 (recovery ranking) | 4 | M | Medium |
| 6 (batch banner) | — | M | Medium (new endpoint) |
| 7 (inbox grouping) | 4 | M | Low |
| 8 (case tabs) | — | M | Low |
| 9 (density/time) | 1 | S | Low |
| 10 (glosses) | — | S | Low |

**Suggested PRs:** PR1 = Steps 1–3+9 (state language) · PR2 = Steps 4+10 (buttons) · PR3 = Steps 5+6 (recovery) · PR4 = Steps 7+8 (navigation density).

## 4. Verification Checklist (per step, before merge)

- [ ] Keyboard-only traversal reaches every action; focus visible
- [ ] No filled button count >2 per view/row (screenshot per page)
- [ ] All status cells non-empty; identical wording for identical states across pages
- [ ] Playwright smoke: case with `pending_create` shows ranked recovery block
- [ ] Existing tests in `backend/tests/` pass (Step 6 adds endpoint test)
- [ ] Console error-free navigation across Overview → Inbox → Cases → Case → Upload → Settings
