# Explicit SOP rule scope and comparison contracts

Status: implemented in isolation; production activation is separate.

## Step42 policy extension

The generic policy union now supports text, visual, date and money checks for
any configured document family. Policies bind validated schema paths, category,
family and registered context applicability. Unknown context values fail rather
than silently excluding the rule. Existing rules and pins are not auto-converted.

Visual checks support presence/completeness, signer-region placement, all-page
marks and two-region consistency. Missing evidence fails; uncertain evidence
requires visual review. Presence alone never proves signature consistency.
A consistency PASS requires recorded observations of both source regions,
including two distinct regions when they are on the same document.

Date checks use explicit equality or on-or-after semantics. Money checks require
amount and currency on both sides, positive finite amounts, ISO currency codes
and explicit decimal/thousands separators. Nonvisual uncertainty fails and cannot
be approved through visual review. Numeric values are never locale-reformatted.

Family score groups configure Total A/B membership. Account Opening retains all
six categories and Forex its four. Every applicable PASS earns one point; FAIL
zero; pending visual reviews remain in possible points. Native report summary
flags retain their existing meaning. Optional supporting_paths configure the two
signature evidence fields used by account identity conditions.

Settings offers draft editors for these policies and score groups. Validation
runs before publication; old publications remain immutable. Native checks keep
the captured compatibility catalog, and configured field checks do not invent a
PASS for fields without an approved check. These boundaries supersede the
historical pending-work statements below.



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

Supported old comparisons can now be converted through the explicit draft-only
upgrade tool documented in COMPARISON_UPGRADE.md. Conversion preserves IDs and
uses a validated `rule_order` to preserve finding/report order. No startup upgrade
or automatic publication is performed. Saved-data verification covered 36
eligible cases and 5,623 ordered findings with no state or score differences;
18 legacy cases were blocked by current validation and 13 had no supported rules.

New scope policies persist in dedicated
publication-scoped family and membership tables through migration 0003. Empty
family selections and rule order survive reconstruction. The settings upgrade
preview, field-binding selectors and single-context applicability editing are
implemented in isolation. Multi-condition policies, non-text comparisons and
new-rule creation remain pending. See UPGRADE_PREVIEW.md.

The read-only `shadow_comparisons` command loaded 67 restored cases and verified
61 decisive plain-text match outcomes through the integrated runtime with zero differences in status, eligibility and category. It explicitly skipped
5,858 unsupported rule occurrences and 55 unresolved outcomes. This is subset
coverage only: identifiers, companion fields, optional-document applicability,
visual evidence and complex rules still require separate acceptance checks.
