-- Fixes approve_hitl's hardcoded installation_id bug (app/main.py).
-- The webhook payload carries the correct installation_id
-- (event.installation.id) at the moment GitHub calls us, but that value
-- was never persisted — so by the time a human clicks "approve" in a
-- separate later request, there was nothing to resolve it from, and the
-- code fell back to a hardcoded constant. This column closes that gap.

ALTER TABLE reviews ADD COLUMN installation_id BIGINT;
