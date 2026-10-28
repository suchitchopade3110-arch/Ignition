-- Audit P0-6: the GitHub Checks API is the single status signal for a
-- review. The check run is created when the webhook arrives and concluded
-- at every exit of the review job, so its id lives on the review row.
-- (The doc calls this "Migration 013"; numbered 016 here, after the RLS,
-- index and review_status migrations.)
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS check_run_id BIGINT;
