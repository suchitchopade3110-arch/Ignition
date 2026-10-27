# Evidence

All commands ran in `/home/user/Ignition` (cloud clone; `git rev-parse --show-toplevel` = `/home/user/Ignition`).
Output is verbatim and complete.

## S0.1 — Repo state

Commit: `9aa42a1971d80cd9c844eba1937cfce75c28fba9`

```text
$ date -u +%FT%TZ; git rev-parse --show-toplevel; git rev-parse HEAD; git branch --show-current; git status --porcelain; git log --oneline -5; git merge-base --is-ancestor 9aa42a1 HEAD && echo "9aa42a1 is ancestor of HEAD"
2026-10-27T17:02:54Z
/home/user/Ignition
9aa42a1971d80cd9c844eba1937cfce75c28fba9
claude/wonderful-mayer-9laif6
[git status --porcelain begin]
[git status --porcelain end]
9aa42a1 Merge pull request #54 from suchitchopade3110-arch/claude/narrow-hallucination-retry-loop
4511a94 Write real security page content and fix contact email
36edf9e Merge pull request #53 from suchitchopade3110-arch/claude/narrow-hallucination-retry-loop
a2ee074 Add SECURITY.md with vulnerability disclosure policy
bc93952 Merge pull request #52 from suchitchopade3110-arch/claude/narrow-hallucination-retry-loop
9aa42a1 is ancestor of HEAD
```

Result: HEAD is exactly `9aa42a1`. `git status --porcelain` is empty, so no stash was needed.
The checked-out branch is the sandbox's session branch (`claude/wonderful-mayer-9laif6`), which
points at the same commit as `main`.

## S0.2 — Inputs in place (HARD STOP)

Commit: `9aa42a1971d80cd9c844eba1937cfce75c28fba9`

```text
$ date -u +%FT%TZ; git rev-parse HEAD; ls -la /mnt/user-data/uploads /mnt/attach; find / (excluding /proc /sys /usr /nix toolchains, node_modules) -type f ( -iname "*.patch" -o -iname "*p0-fixes*" -o -iname "*production-readiness*" ); git fetch origin a992389145de27ddeda4da85386a25d7f1e60e3d; scan all origin/* branches for *.patch / docs/audit
2026-10-27T17:03:03Z
9aa42a1971d80cd9c844eba1937cfce75c28fba9
--- ls -la /mnt/user-data/uploads /mnt/attach
/mnt/attach:
total 8
drwxr-xr-x 2 root root 4096 Oct 27 16:59 .
drwxr-xr-x 6 root root 4096 Oct 27 16:59 ..

/mnt/user-data/uploads:
total 8
drwxr-xr-x 2 root root 4096 Oct 27 17:00 .
drwxr-xr-x 5 root root 4096 Oct 27 17:00 ..
--- find (results below; empty = none)
--- find end
--- git fetch origin a992389145de27ddeda4da85386a25d7f1e60e3d
fatal: remote error: upload-pack: not our ref a992389145de27ddeda4da85386a25d7f1e60e3d
exit=128
--- remote branches scanned: 27
--- branch scan end (empty = no matches)
--- test -f docs/audit/ignition-p0-fixes.patch
absent
```

The exact `find` command was:
`find / \( -path /proc -o -path /sys -o -path /usr -o -path /nix -o -path /opt -o -path /root/.rustup -o -path /root/.cargo -o -path /root/.gradle \) -prune -o -type f \( -iname "*.patch" -o -iname "*p0-fixes*" -o -iname "*production-readiness*" \) -print 2>/dev/null | grep -v node_modules`

The branch scan was:
`for b in $(git branch -r --format='%(refname:short)'); do git ls-tree -r --name-only "$b" | grep -iE '\.patch$|docs/audit|production-readiness' | sed "s|^|$b: |"; done | sort -u`
(after `git fetch -q origin '+refs/heads/*:refs/remotes/origin/*'`).

Observation, not command output: the kickoff message contains the patch as inline text, but its
line breaks are gone. The `From a992389...` header, the diffstat and every hunk sit on one line,
so the text is not a byte-faithful copy. S0.2 forbids rebuilding the patch from context text
either way.

Not recorded, because there is no file: SHA-256 of the patch, its first line on disk, and
`git apply --check` output.
