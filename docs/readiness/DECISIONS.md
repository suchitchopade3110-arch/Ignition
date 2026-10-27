# Decisions

One line each: item — choice — reason.

- S0.1 — No stash. — `git status --porcelain` was empty and HEAD is exactly `9aa42a1`.
- S0.2 — Hard stop instead of rebuilding the patch from the kickoff text. — The kickoff rule says to hard stop when the patch arrives only as text. The inline copy also lost its line breaks, so it could not be byte-exact even if rebuilding were allowed.
- S0.2 — Did not regenerate the patch from git. — Commit `a992389` is not on `origin` (`not our ref`), and no branch carries the file.
- S0.2 — Did not write the solutions doc into `docs/audit/`. — The run ends at the patch check. That file is meant to stay untracked, so it would vanish with the sandbox. The human still has the original.
- S0.3, S0.4 — Not run. — S0.2 is a hard stop that ends the run, and both steps come after it.
- All later items — Marked BLOCKED with reason "run ended at S0.2 hard stop" or "depends on S0.2/S1.1". — The kickoff allows only four statuses, and none of these items was started.
- Git — Committed `docs/readiness/` to the sandbox session branch `claude/wonderful-mayer-9laif6` and pushed it, not `fix/prod-readiness-p0`. — S1.1 is the step that creates `fix/prod-readiness-p0` fresh from `9aa42a1` with `git am`. Creating it now just to hold these notes would get in the rerun's way. The cloud sandbox is reclaimed after the session, so uncommitted notes would be lost. `main` was not touched, nothing was force-pushed, and no PR was opened.
