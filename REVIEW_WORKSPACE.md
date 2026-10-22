# Visual review workspace

Open Visual review from the case header, the SOP workflow card, or a report. Route: /cases/{case_id}/review. It applies to every document family through the shared finding evaluation_type.

The pending queue includes eligible VISUAL findings awaiting review. The Reviewed queue shows audited human decisions. Search narrows the queue. Selecting a check shows source observations and related original document pages, with page selection, zoom and an original-document link. For each related document, record the actual inspected page and region. Choose PASS or FAIL (neither is selected automatically), add a rationale, and save. The result is audited and SOP points are recomputed from stored extraction.

Drafts remain in memory while switching checks on the same page. Reload/closing warnings protect unsaved drafts; drafts are not stored after leaving the page. If a report changes, the draft cannot be submitted until its evidence is reloaded. The API also checks the supplied report_id against the latest report. Source-change fingerprints, related-document checks, both-signature evidence, reviewer permissions and maker/checker controls remain enforced. Review errors appear inline as well as in a toast.

The original expandable SOP review form has been removed from the case page. Case context editing remains on the case page because data failures require correction rather than visual approval.

Notifications automatically expire after 5 seconds (success) or 10 seconds (errors). Pointer hover or keyboard focus pauses the remaining lifetime. Duplicate active messages are suppressed and at most three notifications are visible. Timers are cleaned up on unmount. Manual dismiss remains available.
