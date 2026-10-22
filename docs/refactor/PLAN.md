# Refactor plan

- [ ] B0: isolated source baseline, Git commit, database archive and restore rehearsal
- [ ] B1: configuration inventory and regression baseline
- [ ] D1: schema design: family, profile, identity binding, rule, policy, dataset, report binding; immutable publication revisions
- [ ] D2: typed contracts and compatibility compiler to existing payload format
- [ ] M1: explicit idempotent import from current configuration; round-trip equivalence tests
- [ ] R1: configurable grouping and generic SOP policies
- [ ] R2: application services, provider boundaries and explicit prompt inputs
- [ ] R3: independent report read models and dataset registry
- [ ] V1: full regression, saved dataset comparison and parallel evaluation
- [ ] C1: reviewed cutover, health verification and rollback rehearsal

A step is complete only with linked evidence. Distinguish implemented, tested, migrated and activated. Never mark all hard coding removed without inventory closure.

Current implementation milestones (2026-10-22): configuration compatibility persistence and two additive migrations rehearsed; configurable identity policy tested against 67 cases; explicit SOP membership compiled identically across 40 revisions/112 flows. Remaining: typed SOP runtime integration, family-rule tables/UI, service boundaries, datasets/reporting, full regression, public sanitization and cutover. No activation.
