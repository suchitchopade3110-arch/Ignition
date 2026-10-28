-- I-4 (the solutions doc calls this "migration 015"; numbered after 017).
--
-- Let a failed or cancelled review be redelivered for the same SHA: the
-- webhook dedupe index only counts reviews that are still alive.
DROP INDEX IF EXISTS reviews_repo_pr_head_sha_uidx;
CREATE UNIQUE INDEX reviews_repo_pr_head_sha_uidx ON reviews (repo_full_name, pr_number, commit_sha)
  WHERE status NOT IN ('failed', 'cancelled');

-- The webhook event a review was queued with, so reconciliation can
-- re-enqueue a review whose job was lost.
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS event_payload JSONB;

-- When the current status was set; approve_hitl stamps it on its
-- "posting" claim so reconciliation can release a claim stuck > 5 minutes.
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS status_changed_at TIMESTAMP WITH TIME ZONE;
