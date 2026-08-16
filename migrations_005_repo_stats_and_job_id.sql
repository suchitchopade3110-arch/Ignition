-- Two small, unrelated additions bundled in one migration since both are
-- needed to unblock a real end-to-end review run during the Arq/Redis
-- migration (Phase 2, Prompt 2):
--
-- 1. reviews.job_id — persists the Arq job id per review so a later task
--    (task registry / restart reconciliation, Phase 2 Prompt 3) can query
--    "is this job actually still running" independently of Arq's own
--    internal state, per that prompt's explicit requirement.
--
-- 2. repositories.acs_score / last_review_at — repo_repo.update_repo_stats()
--    was already being called from the review pipeline's finalize_and_post
--    step, but the method didn't exist on RepoRepository and these columns
--    didn't exist on `repositories` either — every review that reached a
--    normal completion crashed with AttributeError there and got marked
--    "failed" despite actually succeeding. Pre-existing bug, found while
--    extracting the pipeline into app/services/review_pipeline.py; fixed
--    here because it blocked verifying a real end-to-end run. Note
--    RepoRepository.list_repos() already computes these dynamically from
--    the reviews table and does NOT read these columns back — they're a
--    write-only cache for now, kept only so update_repo_stats has
--    somewhere real to persist to instead of crashing.

ALTER TABLE reviews ADD COLUMN job_id TEXT;

ALTER TABLE repositories ADD COLUMN acs_score NUMERIC(5,2);
ALTER TABLE repositories ADD COLUMN last_review_at TIMESTAMP WITH TIME ZONE;
