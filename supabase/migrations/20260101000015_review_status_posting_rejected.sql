-- Audit P1-6: HITL approve/reject become compare-and-set transitions.
--   waiting_hitl -> posting  (one approve request claims the review)
--   posting      -> completed (comment posted) or back to waiting_hitl (post failed)
--   waiting_hitl -> rejected (a maintainer dismissed it)
-- (The solutions doc calls this "Migration 014"; numbered 015 here because
-- 013 is RLS and 014 is the HITL-outcomes index.)
ALTER TYPE review_status ADD VALUE IF NOT EXISTS 'posting';
ALTER TYPE review_status ADD VALUE IF NOT EXISTS 'rejected';
