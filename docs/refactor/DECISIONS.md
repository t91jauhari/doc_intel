# Architecture decisions

2026-10-22: modular monolith with workers. Keep existing orchestration initially. No microservice split or full event sourcing.
2026-10-22: isolated sibling checkout, separate state; current application continues unchanged.
2026-10-22: normalized configuration entities with immutable published revisions, initially compiled into legacy payloads to avoid changing extraction execution and case pins simultaneously.
2026-10-22: baseline backup contains sensitive operational data; keep local, excluded from Git. Database archive is not an object-storage backup.
