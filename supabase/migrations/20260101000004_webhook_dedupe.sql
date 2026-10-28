-- Webhook idempotency: a duplicate delivery for the same (repo, PR, head
-- commit) must not spawn a second LangGraph run or post a second comment.
--
-- Enforced as a DB-level uniqueness constraint rather than an app-level
-- "check then insert" so two near-simultaneous deliveries racing each
-- other are still safely serialized by Postgres, not by hoping the app
-- process checks first. app/main.py::github_webhook catches the resulting
-- unique-violation and treats it as a no-op, not an error.

CREATE UNIQUE INDEX reviews_repo_pr_head_sha_uidx
    ON reviews (repo_full_name, pr_number, commit_sha);
