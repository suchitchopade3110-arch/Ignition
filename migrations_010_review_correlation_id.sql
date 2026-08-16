-- Phase 3 Prompt 1: structured/correlated logging. Distinct from `id`
-- (the review's primary key) because they aren't always the same value —
-- a duplicate webhook delivery (see migrations_004_webhook_dedupe.sql)
-- gets its own X-GitHub-Delivery-derived correlation_id for its own log
-- trace, while resolving to the SAME existing review id. Persisted here so
-- later legs (HITL approve/reject, the SSE stream endpoint) can look it
-- back up and keep logging under the same correlation ID a webhook
-- request started, not just for the lifetime of that one HTTP request.

ALTER TABLE reviews ADD COLUMN correlation_id TEXT;
