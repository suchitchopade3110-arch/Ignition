"""
Added-line numbers per file, from a unified diff's hunk headers (P2
auto-fix). GitHub accepts an inline review comment only on a line in the
PR's diff; a suggestion is only meaningful on a line the PR added.
"""
import re

_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def added_lines(diff_text: str) -> dict[str, set[int]]:
    """{path at head: line numbers (head side) the PR added}. Deleted files
    have no head path and are left out."""
    out: dict[str, set[int]] = {}
    path: str | None = None
    line_no = 0
    for line in (diff_text or "").splitlines():
        if line.startswith("diff --git"):
            path = None
        elif line.startswith("+++ "):
            target = line[4:].strip()
            path = target[2:] if target.startswith("b/") else None  # "/dev/null": deleted
        elif line.startswith("@@"):
            m = _HUNK.match(line)
            line_no = int(m.group(1)) if m else 0
        elif path is None or line.startswith("---"):
            continue
        elif line.startswith("+"):
            out.setdefault(path, set()).add(line_no)
            line_no += 1
        elif line.startswith(" "):
            line_no += 1
        # "-" lines and "\ No newline" don't advance the head side
    return out
