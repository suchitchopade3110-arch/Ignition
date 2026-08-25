from app.graph.state import ReviewState
from app.services.github_client import GitHubClient

BANNED_IMPORT_PATTERNS = ["eval(", "child_process.exec("]


def agent_1_gate(state: ReviewState, diff_fetcher=None) -> dict:
    violations = list(state.ast_payload.hard_rule_violations)

    diff_text = ""
    try:
        if diff_fetcher is None:
            client = GitHubClient(installation_id=state.installation_id)
            diff_text = client.get_pr_diff(state.repo_full_name, state.pr_number)
        else:
            diff_text = diff_fetcher(state)
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            "Failed to fetch PR diff; semantic agents will run without code context"
        )

    # Deterministic banned-pattern scan of the actual diff text — added
    # lines only, so this can't reject a PR for a pattern that was already
    # present before the change. Was defined but never applied; the AST
    # analyzer's own hard_rule_violations (checked above) cover its own
    # findings, but this is the gate's one direct check against the diff.
    added_lines = "\n".join(
        line for line in diff_text.splitlines() if line.startswith("+") and not line.startswith("+++")
    )
    for pattern in BANNED_IMPORT_PATTERNS:
        if pattern in added_lines:
            violations.append(f"banned pattern introduced: {pattern}")

    if violations:
        return {
            "hard_rule_violation": True,
            "rejection_reason": "; ".join(violations),
            "diff_text": diff_text,
        }

    return {"hard_rule_violation": False, "diff_text": diff_text}