"""
Agent 1 — deterministic hard-rule gate. No LLM, no network.

Two checks, both against the AST analyzer's diff-scoped output:
  1. hard_rule_violations — the analyzer reports only violations on lines
     this PR ADDED, found by walking real CallExpression nodes with import
     bindings resolved (eval, child_process.exec/execSync incl. aliased and
     destructured require). This replaced a substring scan of the diff text
     that both over-fired (`retrieval(` contains `eval(`) and under-fired
     (`const { exec } = require("child_process")`) — audit P1-9.
  2. boundary-spec layer crossings on edges whose importing file changed.

The diff text is NOT re-fetched here: review_pipeline already fetched it
into state.diff_text, and re-fetching could overwrite it with "" on a
GitHub hiccup, silently blinding every semantic agent (audit P2).
"""
from app.graph.state import ReviewState
from app.graph.verification.boundary_spec import check_boundary_violations


def agent_1_gate(state: ReviewState) -> dict:
    violations = list(state.ast_payload.hard_rule_violations)

    # Deterministic boundary-spec check (app/graph/verification/boundary_spec.py):
    # a dependency edge that crosses a layer boundary the spec declares
    # disallowed is a hard rule violation, checked by exact glob match
    # against the real dependency graph, no LLM involved.
    #
    # Scoped to edges this PR's diff actually introduces (from_file in
    # changed_files), the same scoping diff_scoped_dependency_count uses for
    # ACS — not the whole ast_payload.dependency_graph. That payload can
    # carry edges from anywhere in the repo (see that function's docstring);
    # without this scoping, a pre-existing violation the PR never touches
    # would hard-reject every unrelated PR that happens to share an AST
    # payload with it, forever, which isn't "this PR introduced a hard
    # violation" — the only claim the gate is meant to make.
    boundary_spec = state.boundary_spec  # the reviewed repo's own spec (audit P1-10)
    changed_files = set(state.ast_payload.changed_files)
    diff_scoped_edges = [
        edge for edge in state.ast_payload.dependency_graph if edge.from_file in changed_files
    ]
    for violation in check_boundary_violations(diff_scoped_edges, boundary_spec):
        violations.append(
            f"boundary violation: {violation.from_file} ({violation.from_layer}) -> "
            f"{violation.to_file} ({violation.to_layer}) is a disallowed layer crossing"
        )

    if violations:
        return {"hard_rule_violation": True, "rejection_reason": "; ".join(violations)}
    return {"hard_rule_violation": False}
