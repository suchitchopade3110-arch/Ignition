-- Audit P1-1: dashboard login moves to the GitHub App's own OAuth flow.
-- With "expire user authorization tokens" on, the user token lasts 8 hours
-- and comes with a refresh token; both are stored Fernet-encrypted (the
-- app encrypts them; github_access_token keeps its TEXT type).
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS github_token_expires_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS github_refresh_token TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS github_refresh_token_expires_at TIMESTAMP WITH TIME ZONE;
