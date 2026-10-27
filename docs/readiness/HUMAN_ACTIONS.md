# Human actions

## Migrations to run and env vars to set

None. This run stopped at S0.2, before any code changed, so there are no new migration files and
no new env vars. Do not change Render, Supabase or the GitHub App because of this run.

## Unblock S0.2 (do this before re-running the kickoff)

**Why the run stopped:** the two attachments never reached the cloud sandbox as files.
`/mnt/user-data/uploads` was empty. The patch arrived only as text pasted into the message, with
its line breaks collapsed, and the kickoff forbids rebuilding it from text. Commit `a992389` (the
patch's `From` line) is not on GitHub, so it can't be fetched either.

Pick one of these options.

### Option A: run the kickoff on your Windows machine (the original plan)

1. Where: your PC, in `C:\Users\SUCHIT CHOPADE\OneDrive\Desktop\Ignition\ignition_backend`.
2. Pause OneDrive sync, then paste the kickoff into a local Claude Code session with the two
   files attached as files.
3. Expected result: S0.2 records a SHA-256 for the patch, and `git apply --check` prints nothing.

### Option B: put the inputs on a GitHub branch for a cloud run

A browser upload stores the file exactly as-is, so the cloud agent can copy it byte-for-byte.

1. Where: PowerShell, in the folder that holds the patch. Record its hash:
   `Get-FileHash .\ignition-p0-fixes.patch -Algorithm SHA256`
2. Where: https://github.com/suchitchopade3110-arch/Ignition.
   - Open the branch dropdown, type `inputs/prod-readiness`, and click
     **Create branch inputs/prod-readiness from main**.
   - On that branch, click **Add file → Upload files**. Drop in `ignition-p0-fixes.patch` and
     the solutions doc, saved as `production-readiness-solutions.md`.
   - Choose **Commit directly to the inputs/prod-readiness branch**.
3. Where: the kickoff text, before you paste it. Replace the "Two files are attached" bullet
   with:
   > The two inputs are on branch `inputs/prod-readiness`: `ignition-p0-fixes.patch`
   > (SHA-256 `<hash from step 1>`) and `production-readiness-solutions.md`. In S0.2, copy them
   > with `git fetch origin inputs/prod-readiness` and then
   > `git cat-file blob FETCH_HEAD:ignition-p0-fixes.patch > docs/audit/ignition-p0-fixes.patch`.
   > Confirm `sha256sum` matches the hash above before going on.
4. Expected result in the rerun's `EVIDENCE.md` → S0.2:
   - The SHA-256 matches your step-1 hash.
   - The first line is `From a992389145de27ddeda4da85386a25d7f1e60e3d Mon Sep 17 00:00:00 2001`.
   - `git apply --check docs/audit/ignition-p0-fixes.patch` prints nothing.

The patch trailer names the Claude session that produced it (`session_016V9wH5XS2HGoi1KM6F41JY`).
If that session is still open, the original file may still be in it, which is useful if you no
longer have a local copy.

## Stage runbooks (migrations, Render env, GitHub App, live checks)

Not written yet. The rerun produces them once it implements the items in each stage.
