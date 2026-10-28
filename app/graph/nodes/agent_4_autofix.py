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
from app.services.diff_lines import added_lines
from app.services.prompt_safety import sanitize_narrative

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
        return {"autofix_posted": 0, "autofix_failed": 0}

    # One COMMENT review per head SHA (P2 auto-fix). Inline only where the
    # PR added the line (GitHub 422s anything else); the rest are listed in
    # the review body as text.
    added = added_lines(state.diff_text)
    inline = [f for f in resolved_patches if f.line in added.get(f.file_path, ())]
    as_text = [f for f in resolved_patches if f not in inline]
    comments = [
        {"path": f.file_path, "line": f.line, "side": "RIGHT", "body": f"```suggestion\n{f.suggested_patch}\n```"}
        for f in inline
    ]
    body = ["Suggested fixes from Ignition."]
    if as_text:
        body += ["", "These are on lines this PR didn't add, so they can't be inline suggestions:", ""]
        for f in as_text:
            location = f"{f.file_path}:{f.line}" if f.line is not None else f.file_path
            body += [f"- `{location}`: {sanitize_narrative(f.description)}", "", "```", f.suggested_patch, "```"]

    from app.services.github_client import GitHubClient

    client = GitHubClient(installation_id=state.installation_id)
    try:
        client.post_suggestion_review(
            repo_full_name=state.repo_full_name, pr_number=state.pr_number, head_sha=state.head_sha,
            body="\n".join(body), comments=comments, bot_login=client.bot_login,
        )
    except Exception:
        logger.exception("Failed to post the auto-fix review")
        return {"autofix_posted": 0, "autofix_failed": len(resolved_patches)}
    return {"autofix_posted": len(inline), "autofix_failed": 0}
