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


def test_banned_pattern_inside_line_comment_does_not_reject():
    diff = "+// eval(userInput) is what we used to do here, not anymore\n"
    result = agent_1_gate(_make_state([]), diff_fetcher=lambda s: diff)
    assert result["hard_rule_violation"] is False


def test_banned_pattern_inside_block_comment_does_not_reject():
    diff = "+/*\n+ * eval(x) is dangerous, don't use it\n+ */\n"
    result = agent_1_gate(_make_state([]), diff_fetcher=lambda s: diff)
    assert result["hard_rule_violation"] is False


def test_banned_pattern_inside_string_literal_does_not_reject():
    diff = '+const warningMessage = "never call eval(userInput) in this codebase";\n'
    result = agent_1_gate(_make_state([]), diff_fetcher=lambda s: diff)
    assert result["hard_rule_violation"] is False


def test_banned_pattern_still_rejects_outside_comments_and_strings():
    # The comment/string stripping must not blind the scan to a real,
    # uncommented call sitting right next to a comment mentioning it.
    diff = "+// don't do this:\n+eval(userInput);\n"
    result = agent_1_gate(_make_state([]), diff_fetcher=lambda s: diff)
    assert result["hard_rule_violation"] is True
    assert "eval(" in result["rejection_reason"]


def test_boundary_spec_violation_rejects():
    graph = [
        DependencyEdge(from_file="app/repositories/ledger.py", to_file="app/main.py", imported_symbols=["app"]),
    ]
    result = agent_1_gate(
        _make_state([], dependency_graph=graph, changed_files=["app/repositories/ledger.py"]),
        diff_fetcher=lambda s: "",
    )
    assert result["hard_rule_violation"] is True
    assert "boundary violation" in result["rejection_reason"]
    assert "app/repositories/ledger.py" in result["rejection_reason"]


def test_edge_with_no_boundary_rule_does_not_reject():
    graph = [
        DependencyEdge(from_file="app/graph/state.py", to_file="app/graph/scoring.py", imported_symbols=["compute_acs"]),
    ]
    result = agent_1_gate(
        _make_state([], dependency_graph=graph, changed_files=["app/graph/state.py"]),
        diff_fetcher=lambda s: "",
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
        _make_state([], dependency_graph=graph, changed_files=["app/graph/scoring.py"]),
        diff_fetcher=lambda s: "",
    )
    assert result["hard_rule_violation"] is False