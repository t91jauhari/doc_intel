# Workspace usability release

Implemented 20 October 2026 in the existing document platform. This release updates the frontend and preserves the existing extraction and authorization APIs.

## Configurable

- Workspace preferences offer comfortable/compact information density and expanded/icon-only desktop navigation. Preferences are saved per browser, with a reset action and a storage-unavailable fallback.
- Profile editing is divided into Fields & guidance, Document instructions, and Versions & advanced.
- The add-field form supports text, number and yes/no values, with guidance to retain identifiers as text. Existing schema editing checks display-column shape, uniqueness and coverage before applying it to the draft. Publication still uses the backend's full validation.
- Case lists offer 10, 25 or 50 rows per page and quick views for review, processing and ready states.

## Intuitive and easy to use

- Quick navigation is available from the header and Ctrl/Cmd+K. It searches workspace pages, not customer data; customer search remains in Customer cases.
- Field reprocessing uses numbered steps, field-name search, select-shown/clear actions, removable selection chips and a summary explaining why submission is disabled.
- Optional profile/correction controls are collapsed until needed. Reasons and one-off guidance have distinct labels and helper text.
- Case lists have a readable search area, explicit filter reset, accurate empty states and last-refresh information. The existing SOP filter is explicitly labeled as applying to the current page.
- Mobile navigation moves to the bottom; case rows become stacked summaries on narrow screens. Account/sign-out controls remain available when desktop navigation is collapsed.
- Skip-to-content, active navigation labels, keyboard focus indicators, and dialog Escape/focus handling support keyboard use.

## Reliable

- Background configuration refresh no longer replaces an unpublished draft. Publishing retains optimistic version checks; an externally published version is flagged before another publication.
- Draft discard requires an explicit action and clears editor state. Leaving via a workspace link prompts before discarding unpublished changes; reload/close uses the browser's existing unsaved-change prompt. Drafts are held in memory, not recovered across browser sessions. Browser back/forward navigation is not fully guarded by the link interception.
- Configuration editing is disabled while testing/publishing is in flight.
- Data requests are associated with their query and request sequence. Slow earlier results cannot overwrite the latest filter/search result. Data refreshes on reconnect and when focus returns.
- Field history polls and refreshes after submission. A known active field request prevents overlapping submissions, backed by the existing server check.
- Failed submissions keep selections, reason and guidance. Error and success feedback have distinct icons/text; history-load failures expose a retry.
- Offline controls block new field submissions and configuration publication. The header connection indicator represents browser network status, not a provider-health guarantee.
- Review badges remain visible. Error notifications use an error icon instead of the success icon.

## Verification

The production Docker frontend build includes TypeScript checks. `scripts/workspace_ui_smoke.mjs` exercises persisted preferences, quick navigation, add-field drafting, draft preservation during refresh, link-leave protection, explicit discard, out-of-order searches, case filtering/page size, failed-submission recovery, offline/reconnect behavior, request-history polling/overlap protection, and the 390px mobile layout. Provider submission failures and request-status transitions are intercepted locally; these checks publish no configuration and call no extraction provider.

See the accompanying `UI_Verification.json` for the executed checks. Browser testing uses headless Microsoft Edge on Windows; it is not a cross-browser certification. Existing extraction/reference differences are outside this UI release.

## Apply elsewhere

The UI source archive contains changed/new files only, relative to the existing project. Apply it on top of the extraction-enhancement workspace/source, retain environment/data files, then rebuild and restart the web service with Docker Compose. No new dependency or database migration is required for this UI release.
