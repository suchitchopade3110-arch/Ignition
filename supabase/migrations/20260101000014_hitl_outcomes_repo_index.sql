-- Audit P0-4: HITL severity demotion is now per repo.
-- LedgerRepository.get_consecutive_rejections filters hitl_finding_outcomes
-- by repo_full_name and pattern_key, newest first; this index serves that
-- query directly. (The doc labels this "the index"; numbered 014 here
-- because 013 is the RLS migration.)
CREATE INDEX IF NOT EXISTS hitl_finding_outcomes_repo_pattern_idx
    ON hitl_finding_outcomes (repo_full_name, pattern_key, created_at DESC);
