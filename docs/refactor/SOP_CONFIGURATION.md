# Explicit SOP rule scope and comparison contracts

Status: isolated implementation, not published or activated.

Optional published configuration:

```json
{
  "rule_scope": {
    "family_rule_ids": {
      "forex": ["configured_rule_id"],
      "account_opening": []
    }
  }
}
```

Every registered family must be covered; unknown rule IDs and duplicate
membership entries are rejected. Flow-level `sop_rule_ids` remains the explicit
override, including an empty list. When no explicit scope exists, old versions
retain their original selection behavior. Rule ordering remains the order in the
published rule catalog. Source references remain descriptive for selection under
the new policy. Existing Forex evaluator dispatch still uses source prefixes and
must be migrated separately; this phase does not remove that remaining dependency.

Read-only verification across 40 restored configuration revisions and 112 flow
scopes found no changes in scoped configuration when equivalent explicit
membership was supplied. This verifies scope compilation, not every SOP result.

`configuration/comparison.py` is a pure, typed comparison component. It accepts
configured left/right normalized paths, literal or casefold/whitespace comparison,
and an optional fixed digit-length constraint. Missing and duplicate completed
documents fail explicitly. Values must be text; no automatic number coercion,
fuzzy acceptance, arbitrary expressions or arbitrary regex are supported.

An optional `generic_sop_rules` list now dispatches typed text comparisons through
normal SOP evaluation. New rules declare IDs, labels, families, compared fields,
schema paths for wrapped values, categories, and optional context equality
applicability. Unknown applicability fails; explicit non-applicability excludes
the rule from the denominator. Source REVIEW issues fail as unverified data and
cannot enter visual review. Missing/ambiguous documents fail. Scoring uses the
existing one-point contract and findings render in Excel SOP Details.

Generic rules persist as typed section entries in publication storage. They are
validated before publication/import and cannot collide with existing IDs. Source
reference prefixes do not dispatch or transform these new rules. Existing rules
remain unchanged; there is no automatic conversion. Complex condition policies,
visual rules and broader saved-result coverage remain pending.

New scope policies persist in dedicated
publication-scoped family and membership tables through migration 0003. Empty
family selections and rule order survive reconstruction. The editor is pending.

The read-only `shadow_comparisons` command loaded 67 restored cases and verified
61 decisive plain-text match outcomes through the integrated runtime with zero differences in status, eligibility and category. It explicitly skipped
5,858 unsupported rule occurrences and 55 unresolved outcomes. This is subset
coverage only: identifiers, companion fields, optional-document applicability,
visual evidence and complex rules still require separate acceptance checks.
