# Independent verification

- Date: 2026-10-28T09:08:31Z (run 08:47–09:08Z)
- HEAD: `a3b020f55eb3ff663bbe72f6e1f7ab249309b34d` on `fix/prod-readiness-p0`
- Inputs used: this repository, `docs/readiness/PROGRESS.md` and `docs/readiness/EVIDENCE.md` only.
- Method: every gate re-run in a throwaway `git worktree add --detach` under
  `<scratchpad>/verifier/`, removed afterwards. Mutations were applied only inside those
  worktrees. The main working tree was never modified (`git status --porcelain` is empty before
  and after; `git worktree list` shows only the main tree). No live service was contacted. The only
  network calls were `git ls-remote origin`, `npm ci`/`npm audit`, `bun install`/`bun audit` and `pip-audit`.
- Backend venvs: `/home/user/venv-ign` (no torch) and, for (a)–(c), `/home/user/venv-ign-torch`
  (torch 2.13.0+cu130), matching what the evidence used.
- Backend command: `env -u GITHUB_TOKEN <venv>/bin/python -m pytest tests/ -q -p no:cacheprovider`.
  Analyzer command: `cd ast-analyzer && bun install --frozen-lockfile && bun test`.

VERIFIED items in PROGRESS.md (status starts with VERIFIED): S0.1, S0.2, S0.3, S0.4, S1.1R, S1.2,
S1.5, S3.3, S3.4, S3.7, S3.8, S4.5, S4.6, S4.7, S4.10, S5.1, S5.2, S5.3 (18 items). S4.11 says
"rows 2–8 VERIFIED locally", but its status starts with LIVE-PENDING, so it is out of scope.

---

## S0.1: Repo state

Gate: `git rev-parse --show-toplevel; git rev-parse main; git merge-base --is-ancestor 9aa42a1 HEAD; git status --porcelain --untracked-files=no`

```text
2026-10-28T09:06:30Z
/home/user/Ignition
9aa42a1971d80cd9c844eba1937cfce75c28fba9          (main)
9aa42a1 Merge pull request #54 from suchitchopade3110-arch/claude/narrow-hallucination-retry-loop
9aa42a1 is ancestor of HEAD
9aa42a1971d80cd9c844eba1937cfce75c28fba9          (origin/main)
tracked changes in main tree: (none)
```

**MATCH.** `main` is still exactly 9aa42a1 and the branch starts from it. The tree has no tracked changes.

## S0.2: Inputs and mode

Gate: `git ls-remote origin audit/p0-fixes audit/inputs; git ls-remote --heads origin "audit/*"; git status --porcelain --ignored docs/audit`

```text
2026-10-28T09:06:30Z
exit=0          (no output: audit/p0-fixes, audit/inputs absent)
exit=0          (no audit/* heads)
p0-reference.txt
production-readiness-solutions.md
!! docs/audit/
.git/info/exclude:7:docs/audit/	docs/audit/p0-reference.txt
```

**MATCH.** Neither branch exists on origin, so the mode is REIMPLEMENT. Both input files are present and git ignores them.

## S0.3: Toolchain inventory

Gate: tool `--version` calls and `ls .env frontend/.env* ast-analyzer/.env`

```text
2026-10-28T09:06:31Z
Python 3.13.17 | uv 0.11.32 | bun 1.4.4 | node v22.22.0 | npm 10.9.4 | git 2.43.0
Docker version 29.9.2, build a82e528 | psql (PostgreSQL) 16.15
ls: cannot access '.env': No such file or directory
ls: cannot access 'ast-analyzer/.env': No such file or directory
frontend/.env.example
```

**MATCH.** Every version is identical and there is still no `.env` anywhere. Two notes, neither of which contradicts the item:
(1) `frontend/.env.example` now exists. Commit 314c931 (S2.2) added it after the 9aa42a1 inventory.
It is an example file, not credentials. (2) This verifier's own shell has more
secret-like variable names than the evidence lists (for example `GH_TOKEN` and the AWS names). Only names were
checked. That describes this session's environment, not the repo, and no Supabase, LLM or GitHub App
credentials for the project are present.

## S0.4: Baseline

Gate: clean worktree of 9aa42a1, venv without torch: `pytest tests/ -q`; `--continue-on-collection-errors`;
the counting aid with a stub `sentence_transformers` on PYTHONPATH; `bun test`

```text
2026-10-28T09:06:53Z
9aa42a1971d80cd9c844eba1937cfce75c28fba9
ModuleNotFoundError: No module named 'torch'
      7 E   ModuleNotFoundError: No module named 'sentence_transformers'
!!!!!!!!!!!!!!!!!!! Interrupted: 7 errors during collection !!!!!!!!!!!!!!!!!!!!
--continue-on-collection-errors:
FAILED tests/test_csrf.py::test_hitl_approve_rejects_missing_csrf_header - Mo...
1 failed, 122 passed, 13 warnings, 7 errors in 1.61s
[COUNTING AID: stub] 178 passed, 16 warnings in 5.48s
bun test:  23 pass / 0 fail / Ran 23 tests across 2 files.
```

**MATCH.** The 7 failing modules are the same ones, and the counts are the same: 1 failed / 122 passed / 7 errors; 178 with the stub; 23 analyzer tests.
Only the warning counts differ (13 vs 12, 16 vs 15). That comes from the venv being rebuilt since the baseline, not from a different result.

## S1.1R: Rebuild the P0 patch test-first (a–e)

Gate: GREEN suite in a clean worktree of each sub-step commit, then the item's own test files and
the before/after probe at HEAD.

| Step | Commit | Venv | Evidence | Re-run today |
|---|---|---|---|---|
| (a) | 3ad1716 | torch | 190 passed · 23 pass | `190 passed, 16 warnings in 15.37s` · `23 pass 0 fail` |
| (b) | 46e617e | torch | 193 passed · 33 pass | `193 passed, 17 warnings in 13.26s` · `33 pass 0 fail` |
| (c) | a26005d | torch | 190 passed · 41 pass | `190 passed, 17 warnings in 13.26s` · `41 pass 0 fail` |
| (d) | 9afb1dd | no torch | 193 passed · 41 pass | `ModuleNotFoundError: No module named 'torch'` · `193 passed` · `41 pass 0 fail` |
| (e) | 2c6f6dc | no torch | 195 passed · 41 pass | `ModuleNotFoundError: No module named 'torch'` · `195 passed` · `41 pass 0 fail` |

The item's own tests at HEAD a3b020f (`pytest tests/test_fail_closed.py tests/test_analyzer_auth.py
tests/test_agent_1_gate.py tests/eval/test_golden_eval_gate.py tests/test_embedder_lazy.py
tests/test_deploy_docs.py tests/test_integration_webhook_review_comment.py`):

```text
33 passed, 1 warning in 3.26s
bun test analyzer-git.test.ts      5 pass 0 fail
bun test source.test.ts            2 pass 0 fail
bun test analyzer-versions.test.ts 5 pass 0 fail
bun test analyzer-parsing.test.ts 26 pass 0 fail
```

The doc-table probe (`bun <scratchpad>/probe/probe.ts <analyzer dir> <label>`) gave output identical to EVIDENCE
for BEFORE (9aa42a1) and AFTER (2c6f6dc), and HEAD gives the same AFTER rows:

```text
=== HEAD a3b020f
ROW 1 (PR edits src/user.ts only): changed_files = ["src/user.ts"]  hard_rule_violations = []
ROW 2 (warm vs cold, PR #2): warm user.ts symbols = ["src/user.ts:getUserV2"]  cold = ["src/user.ts:getUserV2"]  identical = true
ROW 3 (two reviews of one repo at once): PR#1 user.ts = ["src/user.ts:getUserById"]  PR#2 user.ts = ["src/user.ts:getUserV2"]  isolated worktrees left behind = []  shared working dirs = (none)
ROW 4 (PR adds destructured exec at runner.ts:4; runner.ts:2 is pre-existing): hard_rule_violations = ["child_process.exec() call found in src/runner.ts:4"]
```

Commits: all five are `commit` objects and ancestors of HEAD. Their stats match the sub-steps: (a) llm_client,
finding_parser, the agents, test_fail_closed.py; (b) analyzer.ts, source.ts, ast_client.py, analyzer-git/source/versions
tests, test_analyzer_auth.py; (c) agent_1_gate.py, analyzer.ts, analyzer-parsing.test.ts, test_golden_eval_gate.py;
(d) vector_store.py, test_embedder_lazy.py; (e) DEPLOY_RENDER.md, test_deploy_docs.py.

**MATCH.** All five pass/fail counts are identical, and the item's tests pass at HEAD.

## S1.2: Mutation check (P0-1)

Gate: in throwaway worktrees of 2c6f6dc and of HEAD, add `APIStatusError` back to the import and the retry
tuple in `app/services/llm_client.py`. Run `pytest tests/test_fail_closed.py -q`, then `git checkout` and run it again.

```text
=== 2c6f6dc  (and identically at a3b020f)
 app/services/llm_client.py | 4 ++--
# MUTANT
ERROR    app.services.llm_client:llm_client.py:74 LLM call failed   (x4)
FAILED tests/test_fail_closed.py::test_non_retryable_400_is_not_retried - Ass...
1 failed, 10 passed, 1 warning in 8.56s
# RESTORED; status: (clean)
11 passed, 1 warning in 0.52s
```

**MATCH.** The mutant is killed by the same test after 4 attempts, and the restored file passes 11/11 at both commits.

## S1.5: Dependency fixes

Gate: clean worktree of b844a4b. Run the backend and analyzer suites, then `npm ci && npm audit --audit-level=high && lint && typecheck && test && build`,
`pip-audit -r requirements.txt` and `bun audit --audit-level=high`.

```text
b844a4bc8eb3e77cd07c548c90bec423e9af89ad
ModuleNotFoundError: No module named 'torch'
199 passed, 18 warnings in 7.96s          |  41 pass 0 fail
npm ci: found 0 vulnerabilities  exit=0
npm audit --audit-level=high: found 0 vulnerabilities  exit=0
lint exit=0 | typecheck exit=0
 Test Files  9 passed (9)
      Tests  50 passed (50)
 ✓ Compiled successfully in 12.4s  exit=0
bun audit: No vulnerabilities found (checked 73 packages)  exit=0
pip-audit: No known vulnerabilities found  exit=0
```

At HEAD: `pytest tests/test_dependencies.py`: `2 passed`.
Commit b844a4b touches requirements*.txt/.in, frontend/package*.json, bun.lock, ci.yml and tests/test_dependencies.py.

**MATCH.**

## S3.3: P1-3 prompt injection

Gate: clean worktree of 493819b, full suites; then `tests/test_prompt_injection.py` at HEAD.

```text
493819b46ce92cb6263b9709fc2a4237822c03e3
281 passed, 46 warnings in 10.28s   |  41 pass 0 fail
HEAD: pytest tests/test_prompt_injection.py -> 17 passed, 1 warning in 0.37s
```

The commit adds app/services/prompt_safety.py, fences in agents 2a/2b/2c/3, the prompt template notes, the
fixture in tests/eval/fixtures.py and tests/test_prompt_injection.py. **MATCH** (281 = evidence; 17 = 13 failed + 4 errors at RED).

## S3.4: P1-4 XSS sink

Gate: clean worktree of 4139a35. Run the backend and analyzer suites, then frontend `npm ci && lint && typecheck && test && build` with the
three env vars from the evidence, then the grep gate.

```text
4139a3570cd661b289c198f260361874bd5b1b2d
282 passed, 46 warnings in 10.55s   |  41 pass 0 fail
npm ci: found 0 vulnerabilities | lint exit=0 | typecheck exit=0
 Test Files  11 passed (11)
      Tests  58 passed (58)
 ✓ Compiled successfully in 11.8s  exit=0
HEAD: grep -rn dangerouslySetInnerHTML frontend/src -> exit=1 (no output)
HEAD: npx vitest run tests/components/markdown-preview.test.tsx -> Tests  5 passed (5)
HEAD: pytest tests/test_review_preview_markdown.py -> 1 passed
```

The commit touches markdown-preview.tsx, its vitest file and test_review_preview_markdown.py. **MATCH.**

## S3.7: P1-10 boundary spec from customer repo

Gate: clean worktrees of 210c53a (the evidence records it as red, because only the file move landed) and of 478ddf0 (GREEN).

```text
210c53a2c95b97058201a9a37891af242827ba1e
FAILED tests/test_agent_3_critic.py::TestVerificationTier::test_2a_edge_matching_a_boundary_rule_is_fact_checked
FAILED tests/test_boundary_spec.py::test_load_default_boundary_spec_reads_repo_root_yaml
FAILED tests/test_prompt_injection.py::test_injection_golden_fixture_keeps_its_floors
... (7 FAILED lines in all)
7 failed, 297 passed, 49 warnings in 13.45s  |  41 pass 0 fail
478ddf05e8d27c54d31c6bd3d9572d6573b20a15
318 passed, 49 warnings in 13.26s  |  44 pass 0 fail
HEAD: pytest tests/test_boundary_spec_from_repo.py -> 14 passed
HEAD: bun test analyzer-boundary-spec.test.ts -> 3 pass 0 fail
```

210c53a is only the rename `ignition.boundaries.yaml => docs/examples/ignition.boundaries.yaml`. 478ddf0 holds the
code, analyzer-boundary-spec.test.ts and test_boundary_spec_from_repo.py. **MATCH** for both commits, including the
recorded red count at 210c53a: 7 failed / 297 passed. The evidence printed 5 of the 7 FAILED lines, but its count line
is the same.

## S3.8: P1-11 bounded 2C fan-out

Gate: clean worktree of 04d8b99, full suites; then the item's tests at HEAD.

```text
04d8b994f06e8e4aadeb4c69b4103e9100a51c00
332 passed, 49 warnings in 15.34s  |  45 pass 0 fail
HEAD: pytest tests/test_agent_2c_bounded.py -> 14 passed, 1 warning in 1.08s
HEAD: bun test analyzer-versions.test.ts -> 5 pass 0 fail
```

The commit touches agent_2c_security.py, popular_npm_packages.txt, refresh_popular_npm.py and test_agent_2c_bounded.py. **MATCH.**

## S4.5: I-6 rate-limit keys

Gate: clean worktree of cd7bcb9, full suites; then `tests/test_rate_limit_keys.py` at HEAD; then real uvicorn
with and without `--proxy-headers --forwarded-allow-ips=*`, called from a non-loopback address.

```text
cd7bcb930f84a24d6156f69784d81c50491ac8fb
381 passed, 1 skipped, 49 warnings in 12.61s  |  45 pass 0 fail
HEAD: pytest tests/test_rate_limit_keys.py -> 4 passed
2026-10-28T09:07:57Z  own address: 192.0.2.2
with flags:    {"client":"198.51.100.7"}
without flags: {"client":"192.0.2.2"}
HEAD:docker-compose.yml:41:    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=*
HEAD:render.yaml:53:    dockerCommand: uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=*
```

**MATCH.**

## S4.6: I-7 worker budgets

Gate: clean worktree of fc8efbd, full suites; then `tests/test_worker_budgets.py` at HEAD.

```text
fc8efbdd5bfda9f4229259da4a9a6fe5582683c3
386 passed, 1 skipped, 49 warnings in 17.49s  |  45 pass 0 fail
HEAD: pytest tests/test_worker_budgets.py -> 5 passed, 1 warning in 5.55s
```

The commit touches app/worker.py, review_pipeline.py, render.yaml and test_worker_budgets.py. **MATCH.**

## S4.7: I-8 SSE heartbeat

Gate: clean worktree of 77ef6f5, full suites; then `tests/test_sse_keepalive.py` at HEAD; then the evidence's
`sse_real_redis.py` against a throwaway local `redis-server --port 6391` (stopped afterwards), run at HEAD.

```text
77ef6f598edb383a8ea845dc5b0dd056cb551571
393 passed, 1 skipped, 49 warnings in 17.84s  |  45 pass 0 fail
HEAD: pytest tests/test_sse_keepalive.py -> 7 passed
2026-10-28T09:07:55Z  a3b020f55eb3ff663bbe72f6e1f7ab249309b34d
items (seconds since subscribe, item): [(0.0, None), (0.2, None), (0.41, None), (0.5, 'agent.started'), (0.7, None), (0.9, None), (1.1, None), (1.31, None), (1.51, None)]
keepalives: 8 events: ['agent.started']
```

**MATCH.** There are 8 keepalives and 1 event, and the stream is capped at about 1.5 s, the same as the evidence.

## S4.10: I-12 blocking audits

Gate: clean worktree of 3a6f4f0, full suites; then all three audits; then `tests/test_dependency_audit.py` at HEAD.

```text
3a6f4f0c57459b1b4d27779fdc8744f872fc5788
418 passed, 1 skipped, 50 warnings in 17.31s  |  45 pass 0 fail
npm audit --audit-level=high: found 0 vulnerabilities  exit=0
bun audit --audit-level=high: No vulnerabilities found (checked 73 packages)  exit=0
python scripts/run_pip_audit.py requirements.txt: No known vulnerabilities found  exit=0
HEAD: pytest tests/test_dependency_audit.py -> 7 passed
HEAD: .github/pip-audit-ignore.txt holds only its 3 comment lines (no ignored IDs)
```

**MATCH.** The pip-audit result is clean without relying on any ignore entry.

## S5.1: Fresh full run

Gate: clean worktree of HEAD a3b020f. The backend runs under `env -i`; then analyzer install + `bunx tsc --noEmit` + test;
then frontend ci/lint/typecheck/test/build; then the three audits and the CI guard.

```text
2026-10-28T08:52:11Z  a3b020f55eb3ff663bbe72f6e1f7ab249309b34d  [status begin][status end]
455 passed, 1 skipped, 3 warnings in 17.54s   exit=0
tsc ok |  52 pass  0 fail | Ran 52 tests across 8 files.   exit=0
npm ci: found 0 vulnerabilities | lint exit=0 | typecheck exit=0
 Test Files  13 passed (13)
      Tests  65 passed (65)
 ✓ Compiled successfully in 13.3s   exit=0
npm audit: found 0 vulnerabilities exit=0
bun audit: No vulnerabilities found (checked 73 packages) exit=0
+ pip-audit -r requirements.txt --strict
No known vulnerabilities found exit=0
CI guard ! grep -E '^(nvidia-|triton|cuda-)' requirements.txt: exit=0
SKIPPED [1] tests/test_fastembed_embedder.py:136: downloads the real model; CI runs it with IGNITION_LIVE_MODEL_TESTS=1
```

**MATCH.** Every number agrees: 455 py, 52 bun, 65 vitest, the build, 3 clean audits and the CI guard. The one skip is the
real-model test that S4.2 records as BLOCKED, not a hidden failure.

## S5.2: Grep gates

Gate: the five `git grep` gates at HEAD.

```text
2026-10-28T08:54:29Z  a3b020f55eb3ff663bbe72f6e1f7ab249309b34d
$ git grep -n dangerouslySetInnerHTML -- frontend/src                 exit=1
$ git grep -n datetime.utcnow                                         exit=1
$ git grep -n -E '^nvidia-|^triton|^cuda-' -- requirements.txt        exit=1
$ git grep -n 'Clean pass' -- . ':!tests' ':!docs/audit'              exit=1
$ git grep -n 'reasoning_effort="none"'                               exit=1
```

**MATCH.** All five are empty. docs/readiness is still untracked, so it does not affect the gates.

## S5.3: History

Gate: `git rev-list --count 9aa42a1..HEAD`, plus a check that every subject has an `<ID>:` prefix, that every ID is in PROGRESS.md, that every
SHA in PROGRESS.md is in history, and that every history commit is named in PROGRESS.md.

```text
2026-10-28T09:08:16Z  a3b020f55eb3ff663bbe72f6e1f7ab249309b34d
commit count 9aa42a1..HEAD: 48
subjects without an '<ID>:' prefix: (end)
IDs used in subjects that are not in PROGRESS.md: (end)
PROGRESS commit SHAs not in history: (end)
history commits not named in PROGRESS.md: (end)
```

**MATCH.** There are 48 commits, none of them unmapped, and every SHA in PROGRESS.md resolves to an ancestor of HEAD.

---

## Summary

18 items checked, 0 mismatches

Mismatches: none.

Gates that could not be re-run: none of the VERIFIED items' gates. (Docker, live Supabase, GitHub and Render
belong to BLOCKED or LIVE-PENDING items only.) Observations that are not mismatches: frontend/.env.example was added later
by S2.2. This verifier's shell carries more secret-like variable names than the S0.3 inventory listed; that is a
session-environment difference, and no project credentials exist. Warning counts differ by ±1 at some commits, while
pass/fail counts are identical everywhere.
