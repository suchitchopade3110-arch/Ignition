# Deploying to Render

This walks through a first deploy using `render.yaml` at the repo root. Two
Render services (`ignition-backend`, `ignition-frontend`) plus one Redis
instance (`ignition-redis`) — see the comments in `render.yaml` for why it's
two services and not the four in `docker-compose.yml`.

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
  (`migrations.sql` first, then `migrations_002_...` through
  `migrations_011_...`) — Supabase's SQL Editor works fine for this, or
  `psql` if you'd rather.
- **An LLM API key** — Groq by default (`LLM_PROVIDER=groq`, free tier
  available), or whatever `app/services/llm_client.py` supports.

`docs/SECRET_ROTATION.md` documents what each of these does and how to
rotate it later.

## 1. First blueprint sync

1. Push this repo (with `render.yaml`) to GitHub if it isn't already there.
2. Render dashboard → **New** → **Blueprint** → pick the repo.
3. Render parses `render.yaml` and shows you three services to create.
   Click through — it'll fail to actually start the backend and frontend
   yet, because the secrets aren't filled in. That's expected; step 3
   below fixes it.

## 2. Fill in the secrets

`render.yaml` marks the credential-shaped vars `sync: false`, which means
Render creates the env var but leaves it blank for you to fill in — it
won't try to manage or overwrite these. On `ignition-backend` → Environment,
set:

| Var | Value |
|---|---|
| `GITHUB_APP_ID` | from your GitHub App's settings page |
| `GITHUB_PRIVATE_KEY` | the full contents of the `.pem` you downloaded, including `-----BEGIN/END-----` lines |
| `GITHUB_WEBHOOK_SECRET` | whatever you set as the App's webhook secret |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | from the OAuth App (or the GitHub App's OAuth section) |
| `LLM_PROVIDER` / `LLM_API_KEY` / `LLM_MODEL_NAME` | e.g. `groq` / your Groq key / `qwen/qwen3-32b` |
| `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` | from your Supabase project settings |

Save changes — this triggers a redeploy of `ignition-backend`.

## 3. Fix the hostnames (only if your service names collided)

`render.yaml` assumes `ignition-backend`/`ignition-frontend` were available
and Render assigned exactly `https://ignition-backend.onrender.com` and
`https://ignition-frontend.onrender.com`. If those names were taken, Render
appends a random suffix instead. Check the actual URLs on each service's
dashboard page, and if they don't match what's baked into `render.yaml`,
update:

- `ignition-backend` → `BACKEND_BASE_URL`, `FRONTEND_BASE_URL`,
  `ALLOWED_ORIGINS` — to the real hostnames.
- `ignition-frontend` → `NEXT_PUBLIC_API_URL` — to the real backend
  hostname + `/api`. **This one needs a rebuild, not just a restart** —
  `NEXT_PUBLIC_*` vars are inlined into the JS bundle at `next build` time.
  After changing it: Manual Deploy → **Clear build cache & deploy**.

## 4. Point GitHub at the deployed backend

- GitHub App → Webhook URL: `https://<your-backend-host>/webhooks/github`
- GitHub OAuth App (or the GitHub App's OAuth callback) → Authorization
  callback URL: `https://<your-backend-host>/auth/github/callback`

## 5. Verify

- `GET https://<your-backend-host>/healthz` — checks real reachability of
  Supabase, the AST analyzer, the LLM provider, and Redis, not just "is the
  process up." All green means the secrets from step 2 are correct.
- `GET https://<your-backend-host>/metrics` — Prometheus scrape target, if
  you're wiring up monitoring.
- Visit the frontend, log in via GitHub, install the App on a test repo,
  open a PR — confirms the webhook → review pipeline → dashboard path
  end-to-end.

## Known rough edges

- **`SESSION_COOKIE_SAMESITE=none`** is required here because
  `ignition-backend.onrender.com` and `ignition-frontend.onrender.com` are
  different sites per the Public Suffix List — a `Lax` cookie (Render's/
  the app's old default) never attaches to the frontend's cross-origin
  `fetch(..., credentials: "include")` calls, and login silently loops. If
  you later move both services behind one custom domain (e.g.
  `api.example.com` + `app.example.com`), you can switch back to `lax`,
  the safer default — see the comment on `session_cookie_samesite` in
  `app/config.py`.
- **Image size**: `requirements.txt` currently resolves `torch` from
  PyPI's default (CUDA-enabled) build via `sentence-transformers`, even
  though this service is CPU-only — see the comment at the top of
  `requirements.in`. This works on Render (nothing here actually loads
  CUDA), but the image is multi-GB larger and slower to build than it
  needs to be. Fixing it means regenerating `requirements.txt` from a
  network context that can reach `download.pytorch.org` — see
  `requirements.in` for the exact command and how to verify it worked.
- **Cold starts on Starter**: Render's Starter plan doesn't spin down like
  Free does, but it's still a single small instance — the first review
  after a deploy will be slower while the AST analyzer's Bun process and
  the embedding model warm up.
