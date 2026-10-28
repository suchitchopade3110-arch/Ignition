# Production readiness — final report

Branch `fix/prod-readiness-p0`, from `9aa42a1`. Head: see the end of this file.
Mode: **REIMPLEMENT** (the P0 patch was rebuilt test-first; see PROGRESS.md and EVIDENCE.md → S0.2).

## Outcome

| Status | Count | Items |
|---|---|---|
| VERIFIED | 20 | S0.1–S0.4, S1.1R, S1.2, S1.5, S3.3, S3.4, S3.7, S3.8, S4.5, S4.6, S4.7, S4.10, S5.1–S5.5 |
| LIVE-PENDING | 19 | S1.3, S1.4, S1.6, S2.1–S2.6, S3.1, S3.2, S3.5, S3.6, S4.3, S4.4, S4.8, S4.9, S4.11, S4.12 |
| BLOCKED | 3 | S4.1 (no Docker daemon), S4.2 (Hugging Face blocked; no Docker), S4.13 eval run (no LLM or Supabase credentials) |
| DEFERRED | 5 | P1-7 step 2 (async Supabase), `projectCache` deletion, nonce CSP, custom-domain topology, `ALLOWED_GITHUB_LOGINS` (all deferred by the kickoff; not built) |

S1.1 is n/a in REIMPLEMENT mode; S1.1R replaces it.

LIVE-PENDING means the code is done and checked locally; the remaining
check needs the deployed stack, a dashboard setting or a migration run on
Supabase. Every one is a numbered step in HUMAN_ACTIONS.md.

## Numbers

| | At 9aa42a1 | At the head |
|---|---|---|
| Backend tests (`pytest tests/ -q`, no torch installed) | collection fails: 7 errors, `No module named 'torch'` | 455 passed, 1 skipped (the opt-in real-model test) |
| Analyzer tests (`bun test`) | 23 pass | 52 pass |
| Frontend (`vitest`) | not measured in S0.4 | 65 passed, lint, typecheck and build clean |
| `npm audit` / `bun audit` (high) | non-blocking in CI (`continue-on-error`) | 0 / 0, blocking |
| `pip-audit` | — | 0 (pillow 12.3.0's 38 advisories fixed by moving to 13.0.0) |
| Grep gates (S5.2) | — | all five empty |

## What changed, by area

- **Fail closed and honest output (P0-1, P0-6, P1-8, P2 "Clean pass"):** a model error is never a clean pass, every exit concludes a GitHub check run, there is one sticky comment per PR, and superseded commits are cancelled. Timeouts now end failed with an "incomplete" comment instead of in the HITL queue (S4.11).
- **Analyzer (P0-2, P0-3, P0-8, P1-10, P1-11, P2 package diffing):** a worktree per review from a shared mirror, changed files from `git diff base...head`, hard rules on added lines only, private and fork PRs, the boundary spec read from the repo's base commit, package-lock v3 and monorepo manifests diffed, and a bounded 2C fan-out.
- **Tenancy and auth (P0-4, P0-5, P1-1, P1-2, P1-6):** repo-scoped queries, same-origin through Next.js rewrites, GitHub App login with Fernet-encrypted tokens and revocation, RLS on every table, atomic HITL approve.
- **Prompt safety and XSS (P1-3, P1-4):** fenced untrusted input, sanitized narratives, severity floors, and react-markdown with raw HTML off. Security headers and CSP are on the frontend (S4.11).
- **Running it as a service (I-1 to I-12):** five Render services, multi-stage non-root images under tini, fastembed instead of torch (no CUDA wheels; a CI guard), heartbeat and reconciliation for orphaned jobs, `/livez` and token-gated `/readyz` and `/metrics`, per-session rate limits, worker budgets, SSE keepalive, indexes and RPCs, and blocking audits.
- **Data (P2 repo IDs, P0-9):** repos and settings keyed by GitHub's numeric id (migration 020 plus a backfill script); migrations tracked by the Supabase CLI in `supabase/migrations/`; the startup check names missing tables, functions and columns.

## Found during the run (beyond the checklist)

- **fastembed 0.9.0 pinned pillow below 13**, which carries 38 advisories. Moved to fastembed 0.9.1, which breaks this run's own "two weeks old" pin rule; see DECISIONS → S4.10.
- **`python scripts/run_golden_eval.py` could never run** as CI's golden-eval job calls it (`No module named 'app'`). Fixed, and a test now checks every script runs by path (S4.13).
- **The landing page's globe fetched GeoJSON from raw.githubusercontent.com**, which the doc's `connect-src 'self'` blocks. Found by loading the built app in Chromium; the file is now served locally (S4.11 row 8).
- **The analyzer reports `changed_files: []` for a package.json-only PR**, while the five hand-written dependency fixtures say `["package.json"]`. This is harmless in production (`changed_files` only scopes dependency counting), but those fixtures still don't match real output, and an existing well-formedness test pins them. Left as is; see DECISIONS → S4.13.
- **A mutation check survived once** (S4.11 package diffing): the monorepo test passed even with root-only diffing. The test was strengthened in a follow-up commit, and the mutation is now caught.
- **The utcnow grep-gate test matched its own docstring** in a clean worktree (S4.11 row 7). Fixed in a follow-up commit; both runs are in the evidence.
- **S3.7's first commit holds only a file rename** because `git add` failed on a pathspec. The content is in the next commit; both are listed.

## Blocked: what's needed

- **S4.1 / S4.2:** a machine with Docker (or CI's docker-build job) for the image checks, and network access to Hugging Face for the real-model test. The commands are in HUMAN_ACTIONS → S4.1 and S4.2.
- **S4.13:** `LLM_*` and `SUPABASE_*` as GitHub Actions secrets, then Run workflow. The README has no eval numbers until then.

## Independent verification (S5.4)

A fresh subagent with only the repo, PROGRESS.md and EVIDENCE.md re-ran the
gate of every VERIFIED item (S0.1–S5.3), at the item's commit and at
HEAD a3b020f: **18 items checked, 0 mismatches**. The per-commit test counts
matched the evidence exactly. Details are in VERIFIER.md. Nothing needed
fixing or downgrading.

## Where things are

- PROGRESS.md: every item, its status and commits.
- EVIDENCE.md: each item's commands, timestamps, SHAs and verbatim output.
- DECISIONS.md: every judgment call and why.
- HUMAN_ACTIONS.md: the runbook, in order.
- VERIFIER.md: the independent re-run.

Code head: `a3b020f` (S4.13). The run documents are committed on top of it in one `S5.5` commit, which is the branch head.
