-- Per-finding-pattern HITL outcome history (app/repositories/ledger.py).
--
-- architecture_ledger (migrations_006) tracks one ACS baseline per review;
-- this table tracks one row per *finding pattern* present in a review a
-- human approved or rejected, so agent_3_critic._decide_hitl_severity can
-- look up "has this specific pattern been rejected repeatedly" and demote
-- its severity, instead of only knowing the outcome of whichever review
-- happened to contain it most recently.

CREATE TABLE hitl_finding_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_full_name TEXT NOT NULL,
    review_id TEXT NOT NULL,
    pattern_key TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('approved', 'rejected')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- get_consecutive_rejections queries by pattern_key ordered by recency.
CREATE INDEX hitl_finding_outcomes_pattern_idx
    ON hitl_finding_outcomes (pattern_key, created_at DESC);
