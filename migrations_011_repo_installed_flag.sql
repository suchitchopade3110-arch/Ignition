-- Tracks whether the GitHub App is currently installed on a repo, driven by
-- the "installation" / "installation_repositories" webhook events (see
-- app/main.py::github_webhook). Previously those events were only
-- acknowledged (202) and otherwise ignored — nothing in the schema could
-- represent "this repo's App access was revoked" at all. Defaults to TRUE
-- (not FALSE) so every existing row — all of which reached this table via
-- an actual pull_request webhook, which cannot happen without the App
-- being installed — is correctly assumed installed rather than requiring a
-- backfill.
ALTER TABLE repositories ADD COLUMN IF NOT EXISTS installed BOOLEAN NOT NULL DEFAULT TRUE;

CREATE INDEX IF NOT EXISTS idx_repositories_installed ON repositories(installed);
