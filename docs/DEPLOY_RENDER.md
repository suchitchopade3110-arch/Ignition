# Deploying to Render

This walks through a first deploy using `render.yaml` at the repo root: one
Render service per process (I-3), so each one is PID 1, gets SIGTERM on a
deploy, and only the frontend and backend face the internet.

| Service | Render type | Plan | Runs |
|---|---|---|---|
| `ignition-frontend` | web | 0.5c-512mb | `next start`; proxies `/api` and `/auth` to the backend (P0-5) |
| `ignition-backend` | web | 0.5c-512mb | `uvicorn` only |
| `ignition-worker` | worker | 1c-2g | `arq app.worker.WorkerSettings` (reviews, the embedder) |
| `ignition-analyzer` | pserv | 1c-2g | Bun + ts-morph, private network only |
| `ignition-redis` | keyvalue | starter (256 MB) | Arq queue, SSE, token cache, rate limits |

The backend and the worker share one image (`Dockerfile`, different start
commands); the analyzer has its own (`ast-analyzer/Dockerfile`). Both run as
UID 10001 under `tini`.

Render is one option, not the only one — everything here is Render-specific
glue around the app's own config (`app/config.py`, `.env.example`); the app
itself doesn't assume Render.

## 0. What you need before starting

None of this is optional — the app will boot without it, but logins,
webhooks, and reviews will all fail. Have these ready:

- **A GitHub App** (App ID, private key, webhook secret) — Settings →
  Developer settings → GitHub Apps → New GitHub App.
- **A GitHub OAuth App** (Client ID/Secret) — for dashboard login. Either a
  separate OAuth App, or enable "Request user authorization (OAuth) during
  installation" on the GitHub App above and reuse its Client ID/Secret.
- **A Supabase project** (URL + service key) — Postgres + pgvector. Run the
  `migrations*.sql` files at the repo root against it, in order
  (`migrations.sql` first, then `migrations_002_...` through the
  highest-numbered file, currently `migrations_020_...`) — Supabase's SQL
  Editor works fine for this, or `psql` if you'd rather. **Skipping 012
  makes every review that has a finding fail** (the Critic reads
  `hitl_finding_outcomes`). **013 turns on row-level security**: before
  running it, confirm `SUPABASE_SERVICE_KEY` is the `service_role` key, or
  the backend loses access too. This prints only the key's role claim:
  `python3 -c 'import os,base64,json; p=os.environ["SUPABASE_SERVICE_KEY"].split(".")[1]; print(json.loads(base64.urlsafe_b64decode(p+"="*(-len(p)%4)))["role"])'`
  — it must print `service_role`. **After 020**, on a project that already
  has repos, run `python scripts/backfill_github_repo_ids.py` once from the
  backend's shell: it fills in GitHub's numeric repo ids, which the
  settings pages now use. Both the web service and the worker
  refuse to start while a required table is missing: their logs name it
  ("Required Supabase tables are missing or unreadable: ...").
- **An LLM API key** — Groq by default (`LLM_PROVIDER=groq`, free tier
  available), or whatever `app/services/llm_client.py` supports.

`docs/SECRET_ROTATION.md` documents what each of these does and how to
rotate it later.

### Tracked migrations (Supabase CLI)

Every migration is also in `supabase/migrations/`, a byte-identical copy
of the root file with a timestamp prefix that keeps the order
(`20260101000001_initial_schema.sql` is `migrations.sql`,
`20260101000002_auth.sql` is `migrations_002_auth.sql`, and so on;
`tests/test_tracked_migrations.py` keeps them in step). With the CLI the
project records what it has applied, instead of you remembering.

- **A new Supabase project:** `supabase link --project-ref <ref>`, then
  `supabase db push`. It applies all of them in order.
- **A project where you already ran migrations by hand:** don't push yet.
  The CLI doesn't know about them and would run them again. Mark each one
  you already applied first, then push the rest:

  ```bash
  supabase link --project-ref <ref>
  # one version per migration already applied, e.g. 001 to 019:
  supabase migration repair --status applied 20260101000001 20260101000002 ... 20260101000019
  supabase migration list   # Local and Remote columns now match up to 019
  supabase db push          # applies only what's left (here: 020)
  ```

  To find what's applied, the startup check names anything missing
  ("Required Supabase tables are missing or unreadable: ...").
  `select column_name from information_schema.columns where table_name = 'repositories'`
  shows whether 011 (`installed`) and 020 (`github_repo_id`) ran.

A new migration gets both files: `migrations_NNN_name.sql` at the root and
its copy `supabase/migrations/20260101000NNN_name.sql`.

## 1. First blueprint sync

1. Push this repo (with `render.yaml`) to GitHub if it isn't already there.
2. Render dashboard → **New** → **Blueprint** → pick the repo.
3. Render parses `render.yaml` and shows you the five services to create.
   Click through — the backend, worker and frontend won't start yet,
   because the secrets aren't filled in. That's expected; step 2 below
   fixes it.

## 2. Fill in the secrets

`render.yaml` marks the credential-shaped vars `sync: false`, which means
Render creates the env var but leaves it blank for you to fill in — it
won't try to manage or overwrite these. On `ignition-backend` → Environment,
set the table below; on `ignition-worker` set the same `GITHUB_APP_*`,
`GITHUB_PRIVATE_KEY`, `LLM_*` and `SUPABASE_*` values (the worker doesn't
need the webhook secret, the OAuth client or `SESSION_TOKEN_KEYS`):

| Var | Value |
|---|---|
| `GITHUB_APP_ID` | from your GitHub App's settings page |
| `GITHUB_PRIVATE_KEY` | the full contents of the `.pem` you downloaded, including `-----BEGIN/END-----` lines |
| `GITHUB_WEBHOOK_SECRET` | whatever you set as the App's webhook secret |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | the **GitHub App's** Client ID and a client secret generated on the App's settings page (dashboard login uses the App's own OAuth flow; no separate OAuth App) |
| `SESSION_TOKEN_KEYS` | one Fernet key (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`); to rotate, put the new key first and the old one second, comma-separated. Login refuses to work without it. |
| `LLM_PROVIDER` / `LLM_API_KEY` / `LLM_MODEL_NAME` | e.g. `groq` / your Groq key / `openai/gpt-oss-120b` (plus `LLM_REASONING_EFFORT=low`) |
| `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` | from your Supabase project settings |

Save changes — this triggers a redeploy of each service you edited.

## 3. Fix the hostnames (only if your service names collided)

`render.yaml` assumes `ignition-backend`/`ignition-frontend` were available
and Render assigned exactly `https://ignition-backend.onrender.com` and
`https://ignition-frontend.onrender.com`. If those names were taken, Render
appends a random suffix instead. Check the actual URLs on each service's
dashboard page, and if they don't match what's baked into `render.yaml`,
update:

- `ignition-backend` → `BACKEND_BASE_URL` and `FRONTEND_BASE_URL` (both the
  real **frontend** hostname — see "Same-origin API" below) and
  `ALLOWED_ORIGINS` (the frontend hostname).
- `ignition-frontend` → `BACKEND_INTERNAL_URL` — the real **backend**
  hostname. **This one needs a rebuild, not just a restart** — the
  rewrites in `frontend/next.config.ts` are built at `next build` time.
  After changing it: Manual Deploy → **Clear build cache & deploy**.
  `NEXT_PUBLIC_API_URL` stays `/api` and `NEXT_PUBLIC_BACKEND_URL` stays
  empty; they never name a hostname.

## 4. Point GitHub at the deployed services

- GitHub App → Webhook URL: `https://<your-backend-host>/webhooks/github`
  (webhooks come from GitHub's servers, not a browser, so they go straight
  to the backend).
- GitHub OAuth App (or the GitHub App's OAuth callback) → Authorization
  callback URL: `https://<your-frontend-host>/auth/github/callback` — the
  **frontend** host, which proxies it to the backend. That is what makes
  the session cookie first-party.

## 5. Verify

- `GET https://<your-backend-host>/livez` → `{"status":"ok"}` — Render's
  health check (no dependencies, I-5).
- `curl -H "Authorization: Bearer $READYZ_TOKEN" https://<your-backend-host>/readyz`
  — checks real reachability of Supabase, the AST analyzer, the LLM
  provider, and Redis (cached 15 s). All green means the secrets from step 2
  are correct. Without the token it answers 401.
- `curl -H "Authorization: Bearer $METRICS_TOKEN" https://<your-backend-host>/metrics`
  — Prometheus scrape target (I-11). In the scrape config set
  `authorization: {credentials: <METRICS_TOKEN>}`. Without the token it
  answers 401; with `METRICS_TOKEN` unset in production it answers 404.
- Visit the frontend, log in via GitHub, install the App on a test repo,
  open a PR — confirms the webhook → review pipeline → dashboard path
  end-to-end.

## Known rough edges

- **Same-origin API (audit P0-5).** `ignition-backend.onrender.com` and
  `ignition-frontend.onrender.com` are different sites per the Public
  Suffix List, so a browser calling the backend directly gets third-party
  cookies: `Lax` never attaches, and Safari blocks even `None`. Instead the
  browser only ever talks to the frontend, and `frontend/next.config.ts`
  rewrites `/api/*` and `/auth/*` to `BACKEND_INTERNAL_URL`. Cookies are
  first-party, `SESSION_COOKIE_SAMESITE=lax` works, and CORS preflights
  disappear. The SSE stream sends `X-Accel-Buffering: no` so the proxy
  doesn't hold events back.
- **Embedder (I-1)**: the worker embeds with fastembed (ONNX Runtime, CPU
  only; no torch or CUDA wheels — CI fails if `nvidia-*`, `triton` or
  `cuda-*` ever reappear in `requirements.txt`). The model is baked into
  the image at build time, so the build needs network access to Hugging
  Face and the running worker doesn't. After switching from the old
  sentence-transformers embedder, run `python scripts/reembed_incidents.py`
  once from the worker's shell (`--dry-run` first).
- **Cold starts**: the first review after a deploy is slower while the
  analyzer's Bun process and the worker's embedding model warm up.
- **Deploys and in-flight reviews**: Render sends the worker SIGTERM and
  waits `maxShutdownDelaySeconds` (60) before SIGKILL; Arq stops taking
  jobs and drains in-flight ones for `job_completion_wait` (50 s).
