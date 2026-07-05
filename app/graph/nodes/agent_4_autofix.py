"""
Auto-Fix Patch Generator. Named in the architectural flow diagram but had
no file in the original skeleton.

Open risk from the PRD: Sub-Graphs A, B, C, and the Critic can each
propose a fix touching the same lines, producing a broken diff if applied
naively. This node is where that sequencing/conflict-detection rule lives
— isolated on purpose so the conflict logic can be hardened independently
without touching the Critic's synthesis logic.
"""
from collections import defaultdict

from app.graph.state import ReviewState, Finding


def _detect_line_conflicts(findings: list[Finding]) -> dict[str, list[Finding]]:
    """Groups findings that propose patches touching the same file+line."""
    by_location: dict[str, list[Finding]] = defaultdict(list)
    for f in findings:
        if f.suggested_patch and f.line is not None:
            by_location[f"{f.file_path}:{f.line}"].append(f)
    return {loc: fs for loc, fs in by_location.items() if len(fs) > 1}


def _resolve_conflict(conflicting: list[Finding]) -> Finding:
    """
    Simple deterministic tie-break: highest severity wins. Not a complete
    solution (documented as an open risk in the PRD) — but deterministic
    beats arbitrary, and it's isolated here for easy replacement later.
    """
    severity_rank = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    return max(conflicting, key=lambda f: severity_rank[f.severity])


async def agent_4_autofix(state: ReviewState) -> dict:
    patchable = [f for f in state.verified_findings if f.suggested_patch]
    conflicts = _detect_line_conflicts(patchable)

    resolved_patches: list[Finding] = []
    seen_locations: set[str] = set()

    for f in patchable:
        loc = f"{f.file_path}:{f.line}"
        if loc in seen_locations:
            continue
        if loc in conflicts:
            resolved_patches.append(_resolve_conflict(conflicts[loc]))
        else:
            resolved_patches.append(f)
        seen_locations.add(loc)

    # TODO: post inline suggestions via GitHubClient.post_inline_suggestion
    return {}