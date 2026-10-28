# Human actions — runbook

Everything here needs a person: a dashboard setting, a secret, a live
service, or a machine this run didn't have (Docker, Hugging Face, an LLM
key). Nothing in this list was done by the run. Do part 1 before deploying
branch `fix/prod-readiness-p0`; the backend refuses to start if a
migration is missing. Each step names its section under "Details by item"
below, which has the exact commands and the expected output.

## 1. Before deploying the branch

1. **GitHub App settings** (GitHub → Settings → Developer settings → GitHub Apps → Ignition):
   - Repository permissions → **Checks: Read and write**, and confirm **Contents: Read**. Installation owners must accept the new permission. → S2.5, S2.6
   - General → note the **Client ID**, generate a **client secret**, set **Callback URL** to `https://<frontend-host>/auth/github/callback`, tick **Expire user authorization tokens**. → S3.2, S2.2
2. **Supabase service key role check** (prints only the role claim; must be `service_role`) before any RLS migration. → S1.4
3. **Migrations 012–020.** Either the Supabase CLI (`supabase link`, then `supabase migration repair` for what's already applied, then `supabase db push`) → S4.12. Or the SQL editor, in order: confirm 012 → S1.6; 013 → S1.4; 014 → S2.1; 015 → S2.4; 016 → S2.5; 017 → S3.2; 018 → S4.3; 019 → S4.8; 020 → S4.11 row 1. Never `db push` before the repair step on an existing project.
4. **Generate three secrets** (each a long random string; keep them in your password manager): `SESSION_TOKEN_KEYS` (a Fernet key) → S3.2; `READYZ_TOKEN` → S4.4; `METRICS_TOKEN` → S4.9.
5. **Optional, recommended: build both images** on a machine with Docker (CI's docker-build job does too) and check UID 10001, tini, and no git/curl in the Python image. → S4.1, S4.2

## 2. Deploy

6. Render → the Blueprint → **Manual sync**. It creates ignition-worker and ignition-analyzer and turns Redis into a `keyvalue` service. Adjust a plan name if Render rejects it. → S4.1
7. Render environment:
   - ignition-backend: `LLM_MODEL_NAME=openai/gpt-oss-120b`, `LLM_REASONING_EFFORT=low` (S1.3); `GITHUB_CLIENT_ID`/`GITHUB_CLIENT_SECRET` from the App (S3.2); `SESSION_TOKEN_KEYS`, `READYZ_TOKEN`, `METRICS_TOKEN` (S3.2, S4.4, S4.9). The blueprint sets the same-origin values (S2.2).
   - ignition-worker: the same secrets as the backend (S4.1 lists them).
   - ignition-frontend: check `BACKEND_INTERNAL_URL`, then **Clear build cache & deploy** (S2.2).
8. Confirm Health Check Path is `/livez` (S4.4) and ignition-analyzer has no public URL (S4.1).

## 3. Right after the deploy

9. Render → ignition-backend → Shell: `python scripts/backfill_github_repo_ids.py --dry-run`, then without `--dry-run`. → S4.11 row 1
10. Render → ignition-worker → Shell: `python scripts/reembed_incidents.py --dry-run`, then without `--dry-run`. → S4.2
11. `/readyz` and `/metrics` return 401 without their tokens and 200 with them. → S4.4, S4.9
12. The four security headers are on the frontend, and the browser console shows no CSP errors. → S4.11 rows 3–8

## 4. Live checks (each closes a LIVE-PENDING item)

13. Model and fail-closed on staging → S1.3 · RLS anon curl and Security Advisor → S1.4 · startup log clean → S1.6
14. Second GitHub account sees nothing → S2.1 · Safari login and HITL approve → S2.2 · three quick pushes give one comment → S2.3 · two simultaneous approves → S2.4 · the Checks tab for each exit path → S2.5 · private-repo and fork PRs → S2.6
15. Merge a baseline, then a regression PR → S3.1 · consent screen, `gAAAA` tokens, revocation → S3.2 · repo settings toggles → S3.5 · two reviews in parallel → S3.6 · ship a boundary spec to test repos → S3.7
16. Deploy during an in-flight review → S4.3 · `dashboard_stats` and HNSW checks, then diff pruning the next day → S4.8 · auto-fix review, timeout and header checks → S4.11 rows 3–8
17. Real embedding model test → S4.2
18. Golden eval with real credentials (repo secrets, then Run workflow); README numbers only from its output → S4.13

## Details by item

### From S1.3 (P0-1)
- Render → ignition-backend (and, after S4.1, ignition-worker) → Environment: set `LLM_MODEL_NAME` to `openai/gpt-oss-120b` and `LLM_REASONING_EFFORT` to `low`. Expected: after redeploy, the worker log shows `LLM call completed` with `model=openai/gpt-oss-120b` on the next real review.
- Staging only: set `LLM_API_KEY` to an invalid value, open a test PR. Expected: the PR comment contains "Review incomplete" and never "Clean pass"; the dashboard row shows status_reason "incomplete: one or more agents failed". Restore the real key afterwards.

### From S1.4 (P1-2)
- **Before running migrations_013_enable_rls.sql**: in a shell that has the Render value of `SUPABASE_SERVICE_KEY` exported, run `python3 -c 'import os,base64,json; p=os.environ["SUPABASE_SERVICE_KEY"].split(".")[1]; print(json.loads(base64.urlsafe_b64decode(p+"="*(-len(p)%4)))["role"])'`. It prints only the role claim. Expected: `service_role`. If it prints `anon`, STOP: replace the env var with the service_role key from Supabase → Project Settings → API first, or the backend loses access.
- Supabase → SQL editor: paste and run `migrations_013_enable_rls.sql`. Expected: `DO`, `REVOKE`, `REVOKE`.
- From any shell: `curl "$SUPABASE_URL/rest/v1/sessions?select=*" -H "apikey: <anon key from Project Settings → API>"`. Expected: `[]` or a permission error, never session rows.
- Supabase → Advisors → Security Advisor. Expected: no "RLS disabled in public" warnings.

### From S1.6 (P0-9)
- Supabase → SQL editor: `select count(*) from hitl_finding_outcomes;`. Expected: a number (0 is fine). An error means migration 012 never ran; run migrations_012_hitl_finding_outcomes.sql first.
- After deploying: the backend and worker logs must not contain "Required Supabase tables are missing or unreadable". If they do, the named tables need their migrations.

### From S2.1 (P0-4)
- Supabase → SQL editor: run `migrations_014_hitl_outcomes_repo_index.sql`. Expected: `CREATE INDEX`.
- Browser: log in to the deployed dashboard with a second GitHub account that has no push access to your test repos. Expected: Dashboard stats are all zero; Repos, Reviews and HITL pages are empty; `/api/reviews?repo=<your repo>` returns 403.

### From S2.2 (P0-5)
- Render → ignition-backend → Environment: `SESSION_COOKIE_SAMESITE=lax`; `BACKEND_BASE_URL` = the frontend's URL (e.g. https://ignition-frontend.onrender.com); `FRONTEND_BASE_URL` = the same frontend URL. (A blueprint sync applies these from render.yaml.)
- Render → ignition-frontend → Environment: `NEXT_PUBLIC_API_URL=/api`, `NEXT_PUBLIC_BACKEND_URL` empty, `BACKEND_INTERNAL_URL` = the backend's URL. Then Manual Deploy → **Clear build cache & deploy** (all three are read at build time).
- GitHub → Settings → Developer settings → your OAuth App (or the GitHub App's "Callback URL"): set the callback to `https://<frontend-host>/auth/github/callback`. The webhook URL stays on the backend host.
- Safari, deployed URLs: log in. Expected: you land on /dashboard without a login loop. In the dev console, `document.cookie` shows `ignition_csrf_token`. Approve a HITL item: the request returns 200.
- Any browser: open a running review's page. Expected: the live timeline updates within about a second of each agent step (SSE through the rewrite).

### From S2.3 (P1-8)
- Optional, Render → ignition-backend (and the worker after S4.1): set `GITHUB_APP_SLUG` to the App's slug (the `<slug>` in github.com/apps/<slug>). If blank, it's looked up from GitHub once per process.
- On a test PR, push three commits in quick succession. Expected: the PR ends with exactly one Ignition comment, for the last SHA. The dashboard shows two reviews with status "cancelled" and reason "superseded by <sha>".
- Open a draft PR. Expected: no review. Mark it "Ready for review". Expected: one review runs.

### From S2.4 (P1-6)
- Supabase → SQL editor: run `migrations_015_review_status_posting_rejected.sql`. Expected: two `ALTER TYPE`. Check with `select enum_range(null::review_status);`; the list must end with `posting, rejected`.
- Deployed dashboard: open the same HITL item in two tabs and click Approve in both at nearly the same moment. Expected: one tab shows success, the other an error (HTTP 409), and the PR has exactly one Ignition comment.

### From S2.5 (P0-6)
- GitHub → Settings → Developer settings → GitHub Apps → (the Ignition App) → Permissions & events → Repository permissions → **Checks: Read and write** → Save. Then each installation's owner must accept the new permission (GitHub emails them; or Settings → Applications → Installed GitHub Apps → Ignition → Review request).
- Supabase → SQL editor: run `migrations_016_reviews_check_run_id.sql`. Expected: `ALTER TABLE`. Check with `select column_name, data_type from information_schema.columns where table_name='reviews' and column_name='check_run_id';` → one row, `bigint`.
- On a test repo with the App installed, open one PR per path and look at the PR's Checks tab for a check named "Ignition":
  - clean change → success "No findings";
  - a change with a real finding → neutral "N findings, highest severity …";
  - add `eval("1")` in a .ts file → failure "Hard rule violated: …", and an Ignition comment with the reason on the PR;
  - a change that triggers a critical finding → action_required "Waiting for human review", and "Details" opens the dashboard review page; approve it there → the check turns neutral/success;
  - set `REVIEW_LATENCY_BUDGET_SECONDS=1` on the worker, open a PR → neutral "Ignition could not finish: timed out …" (restore the value afterwards);
  - temporarily break the analyzer URL or the App key on staging → neutral "Ignition could not finish: failed: …".
- Optional: if a repo marks the "Ignition" check as required, note that infra errors conclude neutral (doesn't block merges), per the doc.

### From S2.6 (P0-8)
- Make sure the App has **Contents: Read** (it already does if reviews show diffs).
- Install the App on a **private** test repo and open a PR there. Expected: the review completes and an Ignition comment is posted; worker logs show no `Authentication failed` / `could not read Username` from git.
- From a **fork** of a test repo (another account), open a PR into the base repo. Expected: the review completes and an Ignition comment is posted.

### From S3.1 (P0-7)
- No settings change: the App already receives `pull_request` events, and "closed" is one of its actions.
- On a test repo: get a PR reviewed (status completed, with an ACS), then merge it. Supabase → Table editor → `architecture_ledger`: one new row for the repo with `risk_scores` = `{"pr": <n>, "sha": "<head sha>"}`. Redeliver the "closed" delivery from the App's Advanced → Recent deliveries: still one row.
- Then open a PR that adds a boundary violation (an import across a forbidden layer). Expected: the review's regression banner shows, and the row has `regression.isRegression = true`.

### From S3.2 (P1-1)
- Generate the encryption key on any machine with Python and `cryptography`:
  `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
  Render → ignition-backend → Environment: add `SESSION_TOKEN_KEYS` = that value (one key, no quotes). Keep a copy in your password manager. To rotate later: set `NEW_KEY,OLD_KEY`, wait a session lifetime (7 days), then drop the old one.
- GitHub → Settings → Developer settings → GitHub Apps → (the Ignition App) → General:
  - Note the **Client ID**; click **Generate a new client secret**.
  - **Callback URL**: `https://ignition-frontend.onrender.com/auth/github/callback` (the frontend origin after S2.2).
  - Tick **Expire user authorization tokens** (recommended) → Save.
  - Render → ignition-backend: set `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` to the App's values (replacing the old OAuth App's). The old OAuth App can be deleted afterwards.
- Supabase → SQL editor: run `migrations_017_session_refresh_tokens.sql`. Expected: three `ALTER TABLE`.
- Everyone is signed out once (old plaintext sessions are refused and deleted). Expected and harmless.
- Live checks:
  - Click "Sign in with GitHub": the consent screen lists no repository scope (only "Verify your GitHub identity" / "Know which resources you can access").
  - Supabase → `select left(github_access_token, 5) from sessions order by created_at desc limit 1;` → `gAAAA`.
  - Revocation (the doc's check: the old token returns 401 from GET /user). Sign in, then in Render → ignition-backend → Shell keep your newest session's token in a variable without printing it:
    ```sh
    TOK=$(python -c "from app.repositories.auth import AuthRepository as A; r=A(); sid=r._db.table('sessions').select('id').order('created_at', desc=True).limit(1).execute().data[0]['id']; print(r.get_session_with_user(sid)['github_access_token'])")
    curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $TOK" https://api.github.com/user   # expect 200
    ```
    Sign out in the browser, then run the same `curl` again → expect `401`. Then `unset TOK`.

### From S3.5 (P1-5)
- Deployed dashboard → a test repo → Settings: turn **Auto-fix** off, open a PR with a mechanical issue. Expected: no inline suggestion comments; the agent timeline has no Auto-Fix row.
- Turn **Security scan** off, push to the PR. Expected: the timeline has no "Security Auditor" row.
- Turn **AI review** off, push again. Expected: the "Ignition" check concludes neutral "AI review disabled for this repo" and no comment is posted or updated.

### From S3.6 (P1-7 step 1)
- After S4.6 is deployed (WORKER_MAX_JOBS=2): open two PRs within a few seconds of each other on a test repo. Expected: both reviews' agent timelines on the dashboard advance at the same time, not one after the other.
- Optional: set `REVIEW_LATENCY_BUDGET_SECONDS=5` on the worker temporarily and open a PR. Expected: the review is cut off at about 5 s (status reason "timed out …"), not later. Restore the value afterwards.

### From S3.7 (P1-10)
- Tell customers (or do it for your own test repos): copy `docs/examples/ignition.boundaries.yaml` to the repo root and edit the layers and rules for that codebase. Without it, the review comment says "No ignition.boundaries.yaml found; boundary checks skipped" and nothing is fact-checked.

### From S4.1 (I-3, I-9) — BLOCKED here: no Docker daemon
- On any machine with Docker, from the repo root at this branch:
  ```sh
  docker build -t ignition-python . 2>&1 | tail -5
  docker build -t ignition-analyzer ./ast-analyzer 2>&1 | tail -5
  docker run --rm ignition-python id -u      # expect 10001
  docker run --rm ignition-analyzer id -u    # expect 10001
  docker run --rm ignition-python sh -c 'command -v git curl; echo exit=$?'   # expect exit=1 (neither present)
  docker run --rm ignition-python ps -o pid,comm 2>/dev/null || docker run --rm ignition-python cat /proc/1/comm   # expect tini
  ```
  (CI's docker-build job also builds both images on every PR.)
- Render: this blueprint replaces the old 3-service one. In the dashboard → the Blueprint → **Manual sync**. Render will propose creating ignition-worker and ignition-analyzer and changing ignition-redis to `keyvalue`. If it rejects a plan name (`0.5c-512mb`, `1c-2g`), pick the closest listed plan with the same CPU/RAM in the sync dialog and note it.
- Fill in ignition-worker's secrets (same values as the backend): GITHUB_APP_ID, GITHUB_PRIVATE_KEY, GITHUB_APP_SLUG (optional), LLM_PROVIDER, LLM_API_KEY, LLM_MODEL_NAME, LLM_REASONING_EFFORT, SUPABASE_URL, SUPABASE_SERVICE_KEY.
- After the deploy: Render → ignition-analyzer → it shows no public URL (private service). Backend RSS at idle (Render → Metrics) should be well under 512 MB.

### From S4.2 (I-1, I-2) — partly BLOCKED here
- The real-model check (Hugging Face is blocked in this sandbox): on any machine with this branch and network,
  `pip install -r requirements.txt -r requirements-dev.txt && IGNITION_LIVE_MODEL_TESTS=1 pytest tests/test_fastembed_embedder.py -k real_model -v` → 1 passed. (CI's test job also runs it.)
- After building the image (S4.1 commands): `docker run --rm ignition-python pip list 2>/dev/null | grep -Ei '^(nvidia|torch|triton|cuda)'` → no output; and
  `docker run --rm ignition-python python -c "from app.rag.vector_store import encode_texts; print(len(encode_texts(['hi'])[0]))"` → `384` (offline, from the baked model).
- Once the new worker is deployed: Render → ignition-worker → Shell:
  `python scripts/reembed_incidents.py --dry-run` (shows how many rows would change), then `python scripts/reembed_incidents.py`. Re-running it is safe; the second run reports `"reembedded": 0`.

### From S4.3 (I-4)
- Supabase → SQL editor: run `migrations_018_requeue_and_partial_dedupe.sql`. Expected: `DROP INDEX`, `CREATE INDEX`, two `ALTER TABLE`. Check: `select indexdef from pg_indexes where indexname = 'reviews_repo_pr_head_sha_uidx';` ends with `WHERE (status <> ALL (ARRAY['failed'::review_status, 'cancelled'::review_status]))`.
- Open a PR on a test repo and, while its review is running (dashboard shows agents moving), trigger a deploy of ignition-worker (Render → Manual Deploy). Expected: the review ends `completed` (or `waiting_hitl`), not `failed` — the old worker drains it and the new one leaves it alone because of the heartbeat.
- Optional: while nothing is stuck, the worker logs should show no "Reconciliation:" lines (the every-minute pass changes nothing).

### From S4.4 (I-5)
- Render → ignition-backend → Environment: add `READYZ_TOKEN` (generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`). Point any uptime monitor that used `/healthz` at `/readyz` with `Authorization: Bearer <token>`.
- After the blueprint sync, Render → ignition-backend → Settings → Health Check Path shows `/livez`.
- `curl -s -o /dev/null -w '%{http_code}\n' https://<backend-host>/readyz` → `401`; with the header → `200` and a JSON body of checks.

### From S4.8 (I-10)
- Supabase → SQL editor: run `migrations_019_reviews_indexes_and_rpcs.sql` **before** deploying this branch's backend (the backend's startup check calls the new functions). Expected: two `CREATE INDEX`, three `CREATE FUNCTION`, three `REVOKE`, `DROP INDEX`, `CREATE INDEX`.
- Check: `select dashboard_stats(array[]::text[]);` → `{"activeReviews" : 0, ...}`; `select indexdef from pg_indexes where indexname = 'incident_embeddings_vector_idx';` contains `USING hnsw`.
- The next day: worker logs show "Pruned old review diffs".

### From S4.9 (I-11)
- Render → ignition-backend → Environment: add `METRICS_TOKEN` (generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`). In the Prometheus scrape config add `authorization: {credentials: <token>}`.
- `curl -s -o /dev/null -w '%{http_code}\n' https://<backend-host>/metrics` → `401`; with `-H "Authorization: Bearer <token>"` → `200`.

### From S4.11 row 1 (P2 repo IDs)
- Supabase → SQL editor: run `migrations_020_github_repo_ids.sql` **before** deploying this branch's backend (the startup check requires the new columns). Expected: two `ALTER TABLE`. Check: `select table_name from information_schema.columns where column_name = 'github_repo_id';` → `repositories`, `repository_settings`.
- After deploying: Render → ignition-backend → Shell: `python scripts/backfill_github_repo_ids.py --dry-run`, then `python scripts/backfill_github_repo_ids.py`. Expected: `{"filled": N, "not_found": [...]}`; a second run reports `"filled": 0`. Any repo under not_found no longer exists on GitHub or no longer has the App installed.
- Check: `select count(*) from repositories where github_repo_id is null;` → 0, apart from the not_found repos. Open the dashboard → Repositories → a repo's settings: it loads, and the request URL is `/api/repos/<number>/settings`.

### From S4.11 rows 3–8 (P2), after deploying this branch
- Auto-fix (row 5): on a test repo with auto-fix on, open a PR whose change Ignition will flag with a fix. Expected: the sticky summary comment appears first, then **one** review titled "Suggested fixes from Ignition." with inline suggestions only on lines the PR added. Re-run the check (or redeliver the webhook) on the same commit: no second suggestion review.
- Timeout (row 3), optional: temporarily set `REVIEW_LATENCY_BUDGET_SECONDS=5` on ignition-worker and open a PR. Expected: the review shows **failed** with "timed out after 5 s" (never in the HITL queue), the sticky comment starts "Ignition Review — incomplete", and the check is neutral. Set the variable back to 60 afterwards.
- Headers (row 8): `curl -sI https://<frontend-host>/ | grep -i -E "content-security-policy|strict-transport-security|x-content-type-options|referrer-policy"` → all four. Log in and open the dashboard, a review and the repo settings with the browser console open: no "Content Security Policy" errors.

### From S4.12 (P0-9 tracked migrations)
- Install the Supabase CLI and `supabase login`. Then, from the repo root: `supabase link --project-ref <your project ref>` (Supabase → Project Settings → General → Reference ID).
- Mark what you've already run by hand. If 001–019 were applied before this branch: `supabase migration repair --status applied 20260101000001 20260101000002 20260101000003 20260101000004 20260101000005 20260101000006 20260101000007 20260101000008 20260101000009 20260101000010 20260101000011 20260101000012 20260101000013 20260101000014 20260101000015 20260101000016 20260101000017 20260101000018 20260101000019`. Leave out any you haven't applied.
- `supabase migration list` → Local and Remote show the same versions through the last one you marked. Then `supabase db push` applies only the rest (for example 020). If you already ran 020 by hand per S4.11, add `20260101000020` to the repair command instead and skip the push.
- Never `supabase db push` before the repair step on a project that already has tables: it would re-run 001 and fail on `CREATE TYPE review_status`.

### From S4.13 (golden eval) — BLOCKED here
- GitHub → repo → Settings → Secrets and variables → Actions: add `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL_NAME`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`. Then Actions → CI → "Run workflow" on `fix/prod-readiness-p0`. The golden-eval job prints per-fixture precision/recall/F1 and an overall line.
- Or locally, with those variables in your shell: `pip install -r requirements.txt && python scripts/run_golden_eval.py`.
- Put numbers in the README only from that output, with its date and commit.
