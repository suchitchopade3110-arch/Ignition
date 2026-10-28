-- P2 "Repo ID collisions" (solutions doc, P2 table). repositories.id is
-- owner_name, so acme_corp/api and acme/corp_api shared one row and one
-- settings row. GitHub's numeric repository id becomes the key: API
-- routes and the review job look repos and settings up by it, and
-- owner/name stay as display fields.
--
-- Nullable until scripts/backfill_github_repo_ids.py has filled existing
-- rows (docs/readiness/HUMAN_ACTIONS.md). New rows always carry it. UNIQUE
-- allows any number of NULLs.

ALTER TABLE repositories ADD COLUMN IF NOT EXISTS github_repo_id BIGINT UNIQUE;
ALTER TABLE repository_settings ADD COLUMN IF NOT EXISTS github_repo_id BIGINT UNIQUE;
