from app.graph.nodes.agent_1_gate import agent_1_gate
from app.graph.state import ReviewState
from app.schemas.ast_payload import ASTAnalyzerPayload


def _make_state(hard_rule_violations: list[str]) -> ReviewState:
    return ReviewState(
        repo_full_name="acme/widgets",
        pr_number=42,
        installation_id=12345,
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=42,
            changed_files=[],
            symbols=[],
            dependency_graph=[],
            hard_rule_violations=hard_rule_violations,
        ),
    )


def test_no_violations_passes_gate():
    result = agent_1_gate(_make_state([]), diff_fetcher=lambda s: "")
    assert result["hard_rule_violation"] is False


def test_violation_rejects():
    result = agent_1_gate(_make_state(["banned import: child_process"]), diff_fetcher=lambda s: "")
    assert result["hard_rule_violation"] is True
    assert "banned import" in result["rejection_reason"]


def test_banned_pattern_in_added_diff_line_rejects():
    diff = "+import { exec } from 'child_process';\n+child_process.exec(cmd);\n"
    result = agent_1_gate(_make_state([]), diff_fetcher=lambda s: diff)
    assert result["hard_rule_violation"] is True
    assert "child_process.exec(" in result["rejection_reason"]


def test_banned_pattern_in_removed_diff_line_does_not_reject():
    # A pattern only present on a `-` (removed) line was already in the
    # codebase before this PR — the PR is removing it, not introducing it.
    diff = "-child_process.exec(cmd);\n+safeExec(cmd);\n"
    result = agent_1_gate(_make_state([]), diff_fetcher=lambda s: diff)
    assert result["hard_rule_violation"] is False