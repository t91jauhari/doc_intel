# Operational local preview

This is a separate local development stack, not the original application or a
production deployment. It uses the accepted backend image, a persistent Docker
volume for SQLite and files, API8100 and the standalone frontend3100. The worker
has an explicit `processing` profile and never connects to production queues.

Before first start, stop intake, back up the current preview SQLite database and
source files, and copy them into the new preview-state volume with ownership for
UID10001. Preserve APP_SECRET so connector encryption and sessions remain valid.
Verify configuration version, document count and source hashes after copying.
Startup does not initialize, migrate or publish business configuration.

Supply PREVIEW_APP_SECRET outside Git and run:

```text
docker compose -f compose.preview.yaml up -d api
docker compose -f compose.preview.yaml --profile processing up -d
```

Enable processing only after configuring the authorized provider connection and
checking its saved model ID. An upload otherwise creates a queued job without a
worker, or fails extraction without credentials. User uploads to the operational
preview will use that provider's limits and billing. Do not submit a real document
merely to test infrastructure without the user's processing authorization.

For acceptance, use an authorized document through the browser: upload/grouping,
classification, extraction, evidence crops, SOP results, required visual review
and report/export. Keep model extraction quality distinct from application job
completion. Record failures and actual paid request counts honestly.

Rollback: stop the new API/worker, preserve their volume, then restore the earlier
preview API on8100 with its retained state. Never run two workers against the
same preview database or use the original application's database/storage/queue.
SQLite is for this bounded local test; production continues to require PostgreSQL,
object storage and Temporal through compose.production.yaml.
