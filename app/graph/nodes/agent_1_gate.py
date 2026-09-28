import re

from app.graph.state import ReviewState
from app.graph.verification.boundary_spec import check_boundary_violations, load_default_boundary_spec
from app.services.github_client import GitHubClient

BANNED_IMPORT_PATTERNS = ["eval(", "child_process.exec("]

# Strips out comments and string-literal contents so the banned-pattern scan
# below only ever matches real code, not a pattern name mentioned in a
# comment or a test fixture string. DOTALL so a `/* ... */` block comment
# spanning multiple added diff lines (each still prefixed with its own `+`)
# is matched as one token.
_STRING_OR_COMMENT_RE = re.compile(
    r"/\*.*?\*/"          # block comment
    r"|//[^\n]*"          # line comment
    r'|"(?:[^"\\\n]|\\.)*"'   # double-quoted string
    r"|'(?:[^'\\\n]|\\.)*'"   # single-quoted string
    r"|`(?:[^`\\]|\\.)*`",    # template literal
    re.DOTALL,
)


def _strip_comments_and_strings(code: str) -> str:
    return _STRING_OR_COMMENT_RE.sub(" ", code)


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
    added_code = _strip_comments_and_strings(added_lines)
    for pattern in BANNED_IMPORT_PATTERNS:
        if pattern in added_code:
            violations.append(f"banned pattern introduced: {pattern}")

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
    boundary_spec = load_default_boundary_spec()
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
        return {
            "hard_rule_violation": True,
            "rejection_reason": "; ".join(violations),
            "diff_text": diff_text,
        }

    return {"hard_rule_violation": False, "diff_text": diff_text}