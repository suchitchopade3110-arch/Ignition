# Secret rotation

There is no secrets manager yet — every credential below lives in
`ignition_backend/.env` (never committed; see the audit at the bottom of
this doc) and rotation is a manual, per-key process. This doc covers the
keys actually present in `.env.example` as of Phase 1. No values are
included anywhere here.

## GITHUB_APP_ID / GITHUB_PRIVATE_KEY

- **Used in:** `app/config.py` → `app/services/github_client.py`
  (`GitHubClient`) and `app/security.py`'s neighbor for signing the App's
  JWT (`Auth.AppAuth`), which is exchanged for short-lived installation
  tokens. This is what lets the backend clone-adjacent operations (posting
  PR comments, reading diffs) act as the GitHub App.
- **To rotate:**
  1. GitHub → Settings → Developer settings → GitHub Apps → your app →
     scroll to **Private keys**.
  2. Click **Generate a private key** — downloads a new `.pem`.
  3. Replace `GITHUB_PRIVATE_KEY` in `.env` with the new key's contents
     (keep the existing multiline/quoting format already used in that
     file).
  4. Back on the same page, **Delete** the old key from GitHub's key list
     — generating a new one does not retire the old one automatically.
  5. Restart the backend so `get_settings()` (which is `@lru_cache`d) picks
     up the new value.
  6. `GITHUB_APP_ID` itself does not rotate — it's a stable identifier for
     the App, not a secret. No action needed for it.
- **If not rotated in time:** GitHub App private keys don't expire on a
  fixed schedule the way OAuth tokens do, but if a key is ever suspected
  compromised (as happened once already during this Phase 1 work — see
  git history), every JWT signed with it can mint installation tokens for
  every repo the App is installed on. There's no grace period: rotate
  immediately, not on a calendar.

## GITHUB_WEBHOOK_SECRET

- **Used in:** `app/security.py`'s `verify_github_signature` — HMAC-SHA256
  verification of the `X-Hub-Signature-256` header on every inbound
  `/webhooks/github` POST. This is the only thing stopping an unsigned
  request from anyone who finds that URL from being treated as a real
  GitHub event.
- **To rotate:**
  1. GitHub → Developer settings → GitHub Apps → your app → **Webhook**
     section → **Change secret**, or generate a new random value yourself
     (`openssl rand -hex 32`) and paste it into the same field.
  2. Update `GITHUB_WEBHOOK_SECRET` in `.env` to match exactly.
  3. Save on GitHub's side first or your side first doesn't matter much,
     but there's a window between the two updates where deliveries will
     401 — expected and harmless (GitHub retries webhook deliveries).
  4. Restart the backend.
- **If not rotated in time:** no expiry; rotate on suspected compromise.
  Until rotated, a leaked secret lets someone forge webhook payloads that
  the backend will accept as genuine GitHub events, including triggering
  arbitrary review runs.

## GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET

- **Used in:** `app/auth.py` — the OAuth login flow (`/auth/github/login`,
  `/auth/github/callback`). Separate credential pair from the App's
  private key above; this one only establishes user identity/session, it's
  never used for server-to-server GitHub API calls.
- **To rotate:**
  1. Same GitHub App settings page → **Client secrets** section →
     **Generate a new client secret**.
  2. Update `GITHUB_CLIENT_SECRET` in `.env`.
  3. Delete the old client secret from GitHub once the new one is
     confirmed working (existing sessions aren't affected — the secret is
     only used at token-exchange time during login, not to validate
     already-issued sessions).
  4. `GITHUB_CLIENT_ID` is not a secret and does not need rotation.
- **If not rotated in time:** a leaked client secret lets an attacker
  impersonate this app in GitHub's OAuth flow (e.g. via a phishing page
  requesting the same scopes) — but they still cannot authenticate as any
  specific user without that user separately approving the consent screen.
  Lower urgency than the App private key or webhook secret, but still
  worth rotating on suspected compromise.

## LLM_API_KEY

- **Used in:** `app/services/llm_client.py`, via `LLM_PROVIDER`/
  `LLM_MODEL_NAME` (Groq by default). Used for every agent call in the
  LangGraph pipeline (structure/logic/security auditors, critic,
  autofix).
- **To rotate:**
  1. Groq console (or whichever provider `LLM_PROVIDER` points at) →
     API keys → revoke the old key, issue a new one.
  2. Update `LLM_API_KEY` in `.env`.
  3. Restart the backend.
- **If not rotated in time:** no fixed expiry on Groq's side currently;
  rotate on suspected compromise or if it leaks into a log/commit. Until
  rotated, review runs keep working with the leaked key, exposing your
  usage/billing to whoever holds it.

## SUPABASE_URL / SUPABASE_SERVICE_KEY

- **Used in:** `app/database.py` → every repository module
  (`app/repositories/*.py`). `SUPABASE_SERVICE_KEY` is the **service
  role** key — it bypasses row-level security entirely, so treat it with
  the same care as a database superuser password, not an anon/public key.
- **To rotate:**
  1. Supabase Dashboard → Project Settings → API → **service_role** key →
     regenerate (Supabase calls this "Reveal"/rotate depending on
     dashboard version — check for a rotate/regenerate action next to the
     key).
  2. Update `SUPABASE_SERVICE_KEY` in `.env`. `SUPABASE_URL` itself only
     changes if the project is recreated (as happened once already during
     this Phase 1 work), not on a rotation cadence.
  3. Restart the backend.
- **If not rotated in time:** no fixed expiry; rotate immediately on
  suspected compromise. A leaked service-role key is full read/write
  access to every table with no RLS protection to fall back on.

## AST_SERVICE_URL

- Not a secret — it's a plain `http://localhost:4000` pointer to the
  sibling Bun process (see the network-boundary fix in
  `ast-analyzer/server.ts`). No rotation needed.

## SESSION_COOKIE_NAME / SESSION_TTL_SECONDS / SESSION_COOKIE_SECURE / BACKEND_BASE_URL / FRONTEND_BASE_URL

- Configuration, not secrets. No rotation needed. (Session *values*
  themselves — the opaque tokens in the `sessions` table — aren't
  long-lived static secrets like the ones above; they expire on their own
  per `SESSION_TTL_SECONDS` and are already scoped per-user.)

---

## `.env` exclusion audit

- `.gitignore` lists `.env` explicitly — confirmed present, not committed.
- `.dockerignore` did not exist before this audit; added one (defense in
  depth — see below for why it wasn't strictly the hole).
- The `Dockerfile` was inspected directly: it never does a blanket
  `COPY . .`. It only copies `requirements.txt`, `app/`, `ast-analyzer/`,
  and `docker-entrypoint.sh` by name — `.env` was never in the build
  context those `COPY` instructions could reach, `.dockerignore` or not.
- Verified by actually building the image and inspecting its filesystem
  (not just reading the ignore files) — see the raw output in this
  session's transcript. `.dockerignore` was added anyway so a future
  Dockerfile change to `COPY . .` doesn't silently reopen this.
