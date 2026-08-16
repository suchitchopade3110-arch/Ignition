-- Phase 2 Prompt 3: task registry + graceful shutdown drain.
-- Records *why* a review was marked failed by the reconciliation/drain
-- logic in app/worker.py and app/services/review_pipeline.py, distinct
-- from ordinary pipeline failures (which already have their own path via
-- the LangGraph execution's except Exception block, and don't need a
-- reason since the exception itself is logged).

ALTER TABLE reviews ADD COLUMN status_reason TEXT;
