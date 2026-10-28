# Production readiness — progress

**Mode: REIMPLEMENT.** Neither `audit/p0-fixes` nor `audit/inputs` exists on origin
(EVIDENCE.md → S0.2). The P0 patch is rebuilt test-first (S1.1R) using
`docs/audit/p0-reference.txt` as a reference and `docs/audit/production-readiness-solutions.md`
as the spec. Both files are untracked (`.git/info/exclude`).

Branch: `fix/prod-readiness-p0`, created from `9aa42a1`.

## How to resume after a restart or compaction

1. `cd /home/user/Ignition && git branch --show-current` should print `fix/prod-readiness-p0`.
2. Re-read this file, the kickoff text (`<scratchpad>/kickoff2.txt`), `docs/audit/production-readiness-solutions.md` and
   `docs/audit/p0-reference.txt`. Continue from the first item that isn't done.
3. Backend tests (from S1.1R(d) on, no torch needed): `export PATH=/home/user/venv-ign/bin:$PATH; env -u GITHUB_TOKEN pytest tests/ -q -p no:cacheprovider`.
   This uses a Python 3.12 venv with no torch. To rebuild it, use
   `uv venv -p 3.12 /home/user/venv-ign`, then run `uv pip install --no-deps` on requirements.txt
   filtered of torch, sentence-transformers, triton and nvidia-* plus `-r requirements-dev.txt` (from S1.5 on; the filter script is
   `<scratchpad>/filter_reqs.py`).
4. Analyzer tests: `cd ast-analyzer && bun test`.
5. Evidence helper: `source <scratchpad>/addev.sh; addev "<title>" <file> "<note>"` appends a
   verbatim block to EVIDENCE.md. Scratchpad:
   `/tmp/claude-0/-home-user-Ignition/543acded-ef06-5806-898a-f444dee61545/scratchpad`.
6. `docs/readiness/` was untracked until S5.5, which removed its `.git/info/exclude` line and committed it. Evidence is captured after
   each item's commit, at that commit's SHA.

## Checklist

| ID | Item | Status | Commit(s) |
|---|---|---|---|
| S0.1 | Repo state | VERIFIED | — (no change) |
| S0.2 | Inputs and mode | VERIFIED (REIMPLEMENT) | — (untracked inputs) |
| S0.3 | Toolchain inventory | VERIFIED | — |
| S0.4 | Baseline | VERIFIED | — |
| S1.1 | Apply the P0 fixes | n/a in REIMPLEMENT mode → see S1.1R | |
| S1.1R | Rebuild the patch test-first (a–e) | VERIFIED | (a) 3ad1716 · (b) 46e617e · (c) a26005d · (d) 9afb1dd · (e) 2c6f6dc |
| S1.2 | Mutation check (P0-1) | VERIFIED | — (no change; check only) |
| S1.3 | P0-1 config residue | LIVE-PENDING (Render env + staging bad-key test) | b287918 |
| S1.4 | P1-2 RLS | LIVE-PENDING (role-claim check + run SQL + anon curl + Security Advisor) | fd50dca |
| S1.5 | Dependency fixes | VERIFIED | b844a4b |
| S1.6 | P0-9 startup table check | LIVE-PENDING (read-only hitl_finding_outcomes check needs credentials) | e6cc4e8 |
| S2.1 | P0-4 tenant scoping | LIVE-PENDING (second GitHub account check) | ad408b4 |
| S2.2 | P0-5 same-origin topology | LIVE-PENDING (Render env, GitHub callback URL, Safari login + HITL approve) | 314c931 |
| S2.3 | P1-8 sticky comment, superseded SHAs, drafts | LIVE-PENDING (three quick pushes on a live PR) | 4f97906 |
| S2.4 | P1-6 atomic HITL approve | LIVE-PENDING (migration 015 + two simultaneous live approves) | f7d5fb4 |
| S2.5 | P0-6 Checks API | LIVE-PENDING (App Checks permission + migration 016 + forced exits on a test PR) | 4b23eb0 · c3ab757 |
| S2.6 | P0-8 live check | LIVE-PENDING (private-repo PR + fork PR on the deployed stack) | — (no code; local coverage from S1.1R(c)) |
| S3.1 | P0-7 merge baselines | LIVE-PENDING (merge a PR, then a boundary-violation PR shows is_regression=true) | b8a56b8 |
| S3.2 | P1-1 GitHub App login + encrypted tokens | LIVE-PENDING (App OAuth settings, SESSION_TOKEN_KEYS, migration 017, consent screen + gAAAA + revoke checks) | 665b858 |
| S3.3 | P1-3 prompt injection | VERIFIED (local: fencing, sanitizer, floors, injection golden fixture with an obedient fake model) | 493819b |
| S3.4 | P1-4 XSS sink | VERIFIED (vitest + grep gate) | 4139a35 |
| S3.5 | P1-5 repo settings applied | LIVE-PENDING (toggle auto-fix off → no suggestions; security scan off → no 2C row) | e33ab25 |
| S3.6 | P1-7 blocking I/O (step 1) | LIVE-PENDING (two live reviews on one worker with WORKER_MAX_JOBS=2; step 2 DEFERRED) | 90d595b |
| S3.7 | P1-10 boundary spec from customer repo | VERIFIED (analyzer test on a real git fixture + Python parsing/gate/Critic tests) | 210c53a · 478ddf0 |
| S3.8 | P1-11 bounded 2C fan-out | VERIFIED (50-package bump → 0 calls; 50 new → 1 call; ≤4 lookups at once) | 04d8b99 |
| S4.1 | Service split + images (I-3, I-9) | BLOCKED (no Docker daemon: `docker build` + `id -u` → HUMAN_ACTIONS; static checks and render.yaml done) | 60165fa |
| S4.2 | I-1/I-2 embedder | BLOCKED (real-model check: Hugging Face 403 here; image `pip list`: no Docker) — code, lockfile and CI guard done | 316db80 · cc6f271 |
| S4.3 | I-4 orphaned jobs | LIVE-PENDING (migration 018 + deploy during an in-flight review) | 3f65a5c |
| S4.4 | I-5 health endpoints | LIVE-PENDING (READYZ_TOKEN on Render; /livez as health check; /readyz 401 without token) | 0f914f7 |
| S4.5 | I-6 rate-limit keys | VERIFIED (local: key function + uvicorn proxy trust) | cd7bcb9 |
| S4.6 | I-7 worker budgets | VERIFIED (local: settings + both budget paths) | fc8efbd |
| S4.7 | I-8 SSE heartbeat | VERIFIED (local, incl. a real Redis) | 77ef6f5 |
| S4.8 | I-10 database work | LIVE-PENDING (run migration 019) | e051a79 |
| S4.9 | I-11 metrics auth | LIVE-PENDING (set METRICS_TOKEN on Render) | 8c28d35 |
| S4.10 | I-12 blocking audits | VERIFIED | 3a6f4f0 |
| S4.11 | P2 batch (8 rows) | LIVE-PENDING (row 1: run migration 020 and the backfill; rows 2–8 VERIFIED locally) | 4eac91a, 7e7e2d2+a3fe82f, c3713a8, a2739b5, 8b3c247, f06e256, 255cd2b+50726d1, a762cf1 |
| S4.12 | P0-9 tracked migrations | LIVE-PENDING (link and repair on the real project) | b806eb5 |
| S4.13 | P0-2 real golden fixtures | BLOCKED (fixtures regenerated and verified; the eval run needs LLM and Supabase credentials) | c880ff7, a3b020f |
| S5.1 | Fresh full run | VERIFIED (a3b020f: 455 py, 52 bun, 65 vitest + build, 3 audits, CI guard) | — |
| S5.2 | Grep gates | VERIFIED (all five empty at a3b020f) | — |
| S5.3 | History | VERIFIED (48 commits, none unmapped) | — |
| S5.4 | Independent verification | VERIFIED (fresh subagent: 18 VERIFIED items re-run, 0 mismatches; VERIFIER.md) | — |
| S5.5 | Report and push | VERIFIED (run documents committed, branch pushed) | the docs/readiness commit |

S1.1R sub-steps: (a) P0-1 fail-closed · (b) analyzer isolation/scoping P0-2/3/8 · (c) P1-9 gate ·
(d) I-1 + P1-7 embedder · (e) P0-9 DEPLOY_RENDER.md.

## Deferred by the doc (not built)

P1-7 step 2 (async Supabase) · `projectCache` deletion · nonce CSP · custom-domain topology ·
`ALLOWED_GITHUB_LOGINS`.
