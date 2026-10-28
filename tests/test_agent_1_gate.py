from unittest.mock import MagicMock

from app.graph.nodes.agent_1_gate import agent_1_gate
from app.graph.state import ReviewState
from app.schemas.ast_payload import ASTAnalyzerPayload, DependencyEdge


def _make_state(
    hard_rule_violations: list[str],
    dependency_graph: list[DependencyEdge] | None = None,
    changed_files: list[str] | None = None,
) -> ReviewState:
    return ReviewState(
        repo_full_name="acme/widgets",
        pr_number=42,
        installation_id=12345,
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=42,
            changed_files=changed_files or [],
            symbols=[],
            dependency_graph=dependency_graph or [],
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








def test_boundary_spec_violation_rejects():
    graph = [
        DependencyEdge(from_file="app/repositories/ledger.py", to_file="app/main.py", imported_symbols=["app"]),
    ]
    result = agent_1_gate(
        _make_state([], dependency_graph=graph, changed_files=["app/repositories/ledger.py"])
    )
    assert result["hard_rule_violation"] is True
    assert "boundary violation" in result["rejection_reason"]
    assert "app/repositories/ledger.py" in result["rejection_reason"]


def test_edge_with_no_boundary_rule_does_not_reject():
    graph = [
        DependencyEdge(from_file="app/graph/state.py", to_file="app/graph/scoring.py", imported_symbols=["compute_acs"]),
    ]
    result = agent_1_gate(
        _make_state([], dependency_graph=graph, changed_files=["app/graph/state.py"])
    )
    assert result["hard_rule_violation"] is False


def test_boundary_spec_violation_outside_diff_does_not_reject():
    # A boundary violation whose from_file this PR never touched is a
    # pre-existing edge somewhere else in the repo's graph, not something
    # this PR introduced — the gate only rejects for what the diff itself
    # did, same scoping as diff_scoped_dependency_count (see scoring.py).
    graph = [
        DependencyEdge(from_file="app/repositories/ledger.py", to_file="app/main.py", imported_symbols=["app"]),
    ]
    result = agent_1_gate(
        _make_state([], dependency_graph=graph, changed_files=["app/graph/scoring.py"])
    )
    assert result["hard_rule_violation"] is False


def _gate_client_returning(monkeypatch, diff: str) -> MagicMock:
    """The old gate re-fetched the diff through GitHubClient; hand it one."""
    client = MagicMock()
    client.get_pr_diff.return_value = diff
    monkeypatch.setattr("app.graph.nodes.agent_1_gate.GitHubClient", lambda installation_id: client, raising=False)
    return client


def test_gate_does_not_substring_match_diff_text(monkeypatch):
    # `retrieval(` contains `eval(` — the old substring scan hard-rejected this.
    diff = "+const docs = retrieval(query);\n"
    _gate_client_returning(monkeypatch, diff)
    state = _make_state([])
    state.diff_text = diff
    assert agent_1_gate(state)["hard_rule_violation"] is False


def test_gate_keeps_pipeline_diff_text_instead_of_refetching(monkeypatch):
    # A GitHub hiccup on a re-fetch used to overwrite the pipeline's diff with "".
    client = _gate_client_returning(monkeypatch, "")
    state = _make_state([])
    state.diff_text = "+export const x = 1;\n"
    result = agent_1_gate(state)
    assert "diff_text" not in result  # state.diff_text is left untouched
    client.get_pr_diff.assert_not_called()
