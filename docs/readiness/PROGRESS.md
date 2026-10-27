# Production readiness — progress

**Run status: HARD STOP at S0.2 (2026-10-27T17:03:03Z).**

The patch `ignition-p0-fixes.patch` never reached the sandbox as a file. It arrived only as text
inside the kickoff message, with its line breaks collapsed (header, diffstat and every hunk run
together on one line). S0.2 says: *"If the patch reached you only as text with no file on disk,
hard stop and say so in `PROGRESS.md`."* Nothing after S0.2 was started. See `EVIDENCE.md` → S0.2
and `HUMAN_ACTIONS.md` → "Unblock S0.2".

Checked before stopping (raw output in `EVIDENCE.md`):

- `/mnt/user-data/uploads` and `/mnt/attach` are empty.
- No `*.patch`, `*p0-fixes*` or `*production-readiness*` file anywhere on the sandbox disk.
- Commit `a992389145de27ddeda4da85386a25d7f1e60e3d` (the patch's `From` line) is not on
  `origin`: `fatal: remote error: upload-pack: not our ref`.
- None of the 27 remote branches carries a `.patch` file or a `docs/audit/` folder.

Repo: `/home/user/Ignition` (cloud clone of suchitchopade3110-arch/Ignition), HEAD `9aa42a1`, clean tree.

## Checklist

| ID | Item | Status | Note |
|---|---|---|---|
| S0.1 | Repo state | VERIFIED | HEAD = 9aa42a1, tree clean, no stash needed |
| S0.2 | Inputs in place | BLOCKED | Hard stop: patch not on disk (only flattened inline text) |
| S0.3 | Toolchain inventory | BLOCKED | Run ended at S0.2 hard stop |
| S0.4 | Baseline | BLOCKED | Run ended at S0.2 hard stop |
| S1.1 | Apply the patch | BLOCKED | Depends on S0.2 |
| S1.2 | Mutation check (P0-1) | BLOCKED | Depends on S1.1 |
| S1.3 | P0-1 config residue | BLOCKED | Depends on S1.1 |
| S1.4 | P1-2 RLS | BLOCKED | Run ended at S0.2 hard stop |
| S1.5 | Dependency fixes | BLOCKED | Run ended at S0.2 hard stop |
| S1.6 | P0-9 startup table check | BLOCKED | Run ended at S0.2 hard stop |
| S2.1 | P0-4 tenant scoping | BLOCKED | Run ended at S0.2 hard stop |
| S2.2 | P0-5 same-origin topology | BLOCKED | Run ended at S0.2 hard stop |
| S2.3 | P1-8 sticky comment, superseded SHAs, drafts | BLOCKED | Run ended at S0.2 hard stop |
| S2.4 | P1-6 atomic HITL approve | BLOCKED | Run ended at S0.2 hard stop |
| S2.5 | P0-6 Checks API | BLOCKED | Run ended at S0.2 hard stop |
| S2.6 | P0-8 live check | BLOCKED | Depends on S1.1 |
| S3.1 | P0-7 merge baselines | BLOCKED | Run ended at S0.2 hard stop |
| S3.2 | P1-1 GitHub App login + encrypted tokens | BLOCKED | Run ended at S0.2 hard stop |
| S3.3 | P1-3 prompt injection | BLOCKED | Run ended at S0.2 hard stop |
| S3.4 | P1-4 XSS sink | BLOCKED | Run ended at S0.2 hard stop |
| S3.5 | P1-5 repo settings applied | BLOCKED | Run ended at S0.2 hard stop |
| S3.6 | P1-7 blocking I/O (step 1) | BLOCKED | Run ended at S0.2 hard stop |
| S3.7 | P1-10 boundary spec from customer repo | BLOCKED | Depends on S1.1 (analyzer changes) |
| S3.8 | P1-11 bounded 2C fan-out | BLOCKED | Run ended at S0.2 hard stop |
| S4.1 | Service split + images (I-3, I-9) | BLOCKED | Run ended at S0.2 hard stop |
| S4.2 | I-1/I-2 embedder | BLOCKED | Depends on S1.1 (lazy import) |
| S4.3 | I-4 orphaned jobs | BLOCKED | Run ended at S0.2 hard stop |
| S4.4 | I-5 health endpoints | BLOCKED | Run ended at S0.2 hard stop |
| S4.5 | I-6 rate-limit keys | BLOCKED | Run ended at S0.2 hard stop |
| S4.6 | I-7 worker budgets | BLOCKED | Run ended at S0.2 hard stop |
| S4.7 | I-8 SSE heartbeat | BLOCKED | Run ended at S0.2 hard stop |
| S4.8 | I-10 database work | BLOCKED | Run ended at S0.2 hard stop |
| S4.9 | I-11 metrics auth | BLOCKED | Run ended at S0.2 hard stop |
| S4.10 | I-12 blocking audits | BLOCKED | Run ended at S0.2 hard stop |
| S4.11 | P2 batch | BLOCKED | Run ended at S0.2 hard stop |
| S4.12 | P0-9 tracked migrations | BLOCKED | Run ended at S0.2 hard stop |
| S4.13 | P0-2 real golden fixtures | BLOCKED | Depends on S1.1 (diff-scoped analyzer) |
| S5.1 | Fresh full run | BLOCKED | Run ended at S0.2 hard stop |
| S5.2 | Grep gates | BLOCKED | Run ended at S0.2 hard stop |
| S5.3 | History | BLOCKED | Run ended at S0.2 hard stop |
| S5.4 | Independent verification | BLOCKED | Run ended at S0.2 hard stop |
| S5.5 | Report and push | BLOCKED | Hard-stop record pushed to the session branch instead; see DECISIONS.md |

## Deferred by the doc (not built)

| Item | Status |
|---|---|
| P1-7 step 2: async Supabase client | DEFERRED |
| Deleting unused `projectCache` and its tests (P0-3) | DEFERRED |
| Nonce-based CSP to remove `'unsafe-inline'` | DEFERRED |
| Custom-domain topology (P0-5 alternative) | DEFERRED |
| `ALLOWED_GITHUB_LOGINS` allowlist (P0-4 optional) | DEFERRED |

## Resuming

After the human completes `HUMAN_ACTIONS.md` → "Unblock S0.2", restart from S0.1 on a fresh
checkout of `9aa42a1`. Nothing from this run needs undoing: no product code changed, no
`fix/prod-readiness-p0` branch was created, `main` was not touched.
