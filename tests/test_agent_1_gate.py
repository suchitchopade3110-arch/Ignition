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
    result = agent_1_gate(_make_state([]))
    assert result["hard_rule_violation"] is False


def test_violation_rejects():
    result = agent_1_gate(_make_state(["banned import: child_process"]))
    assert result["hard_rule_violation"] is True
    assert "banned import" in result["rejection_reason"]