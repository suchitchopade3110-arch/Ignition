"""
Auto-Fix Patch Generator. Named in the architectural flow diagram but had
no file in the original skeleton.

Open risk from the PRD: Sub-Graphs A, B, C, and the Critic can each
propose a fix touching the same lines, producing a broken diff if applied
naively. This node is where that sequencing/conflict-detection rule lives
— isolated on purpose so the conflict logic can be hardened independently
without touching the Critic's synthesis logic.
"""
import logging
from collections import defaultdict

from app.graph.state import ReviewState, Finding

logger = logging.getLogger(__name__)


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

    if not resolved_patches:
        return {}

    from app.services.github_client import GitHubClient

    client = GitHubClient(installation_id=state.installation_id)
    posted_count = 0
    failed_count = 0

    for finding in resolved_patches:
        try:
            client.post_inline_suggestion(
                repo_full_name=state.repo_full_name,
                pr_number=state.pr_number,
                file_path=finding.file_path,
                line=finding.line,
                patch=finding.suggested_patch,
            )
            posted_count += 1
        except Exception:
            logger.exception(
                "Failed to post inline suggestion for %s:%s", finding.file_path, finding.line
            )
            failed_count += 1

    return {"autofix_posted": posted_count, "autofix_failed": failed_count}