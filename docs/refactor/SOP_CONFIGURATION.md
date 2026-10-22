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

This comparison component is not yet dispatched from existing SOP rules. Typed
condition policies, evidence binding, scoring integration and saved-result
comparison are next acceptance gates. The scope policy currently persists as a
versioned publication extension; dedicated family-rule membership rows and the
configuration editor are pending.
