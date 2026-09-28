import pytest

from app.graph.scoring import compute_acs, diff_scoped_dependency_count, is_rule_regression
from app.schemas.ast_payload import DependencyEdge


def test_acs_perfect_score():
    assert compute_acs(total_dependencies=10, total_violations=0) == 100.0


def test_acs_with_violations():
    assert compute_acs(total_dependencies=10, total_violations=2) == 80.0


def test_acs_zero_dependencies_does_not_divide_by_zero():
    # The PRD-flagged edge case: zero dependencies should not raise.
    assert compute_acs(total_dependencies=0, total_violations=0) == 100.0


def test_regression_detected_when_below_baseline():
    assert is_rule_regression(current_acs=70.0, baseline_acs=90.0) is True


def test_no_regression_when_no_baseline_exists():
    # First-ever PR for a repo — nothing to regress against.
    assert is_rule_regression(current_acs=50.0, baseline_acs=None) is False


def test_no_regression_when_score_improves():
    assert is_rule_regression(current_acs=95.0, baseline_acs=90.0) is False


def test_acs_clamped_at_zero_when_violations_exceed_dependencies():
    # A PR can carry more architecture violations than dependency edges in
    # the raw formula's arithmetic; the score must not go negative.
    assert compute_acs(total_dependencies=1, total_violations=5) == 0.0


def _repo_graph(changed_from_file: str, changed_edge_count: int, unrelated_edge_count: int) -> list[DependencyEdge]:
    changed = [
        DependencyEdge(from_file=changed_from_file, to_file=f"x{i}.ts", imported_symbols=[])
        for i in range(changed_edge_count)
    ]
    unrelated = [
        DependencyEdge(from_file="unrelated.ts", to_file=f"y{i}.ts", imported_symbols=[])
        for i in range(unrelated_edge_count)
    ]
    return changed + unrelated


def test_diff_scoped_dependency_count_only_counts_edges_from_changed_files():
    graph = _repo_graph("a.ts", changed_edge_count=3, unrelated_edge_count=497)
    assert diff_scoped_dependency_count(graph, changed_files=["a.ts"]) == 3


def test_diff_scoped_dependency_count_ignores_edges_into_a_changed_file():
    # Scoped by from_file (the importer), not to_file — an edge some
    # unrelated file has *into* a changed file isn't something this diff
    # could have changed.
    graph = [DependencyEdge(from_file="unrelated.ts", to_file="a.ts", imported_symbols=[])]
    assert diff_scoped_dependency_count(graph, changed_files=["a.ts"]) == 0


def test_diff_scoped_dependency_count_zero_when_no_files_changed():
    graph = _repo_graph("a.ts", changed_edge_count=3, unrelated_edge_count=497)
    assert diff_scoped_dependency_count(graph, changed_files=[]) == 0


def test_acs_moves_meaningfully_on_diff_scoped_denominator_not_whole_repo():
    # The bug this redefinition fixes: scored against the whole 500-edge
    # repo, a single violation in a 3-edge diff barely registers. Scored
    # against just the diff's own edges, it swings hard — proving ACS is
    # no longer numerically inert to what the PR itself did.
    graph = _repo_graph("a.ts", changed_edge_count=3, unrelated_edge_count=497)

    whole_repo_score = compute_acs(total_dependencies=len(graph), total_violations=1)
    diff_scoped_total = diff_scoped_dependency_count(graph, changed_files=["a.ts"])
    diff_scoped_score = compute_acs(total_dependencies=diff_scoped_total, total_violations=1)

    assert diff_scoped_total == 3
    assert whole_repo_score > 99.5  # (500-1)/500*100 — barely moves
    assert diff_scoped_score == pytest.approx(66.67, abs=0.01)  # (3-1)/3*100
    assert whole_repo_score - diff_scoped_score > 30  # meaningfully different


def test_regression_fires_on_the_new_diff_scoped_scale_with_retuned_tolerance():
    # A single new violation in a small (5-edge) diff swings ACS by 20
    # points on the new scale — comfortably past the re-tuned 5.0-point
    # default tolerance (app/config.py), so it must still register as a
    # regression even though the drop looks huge next to the old
    # whole-repo-scale tolerance of 1.0.
    baseline_acs = 100.0
    current_acs = compute_acs(total_dependencies=5, total_violations=1)  # 80.0
    assert is_rule_regression(current_acs, baseline_acs, tolerance=5.0) is True


def test_no_regression_when_diff_scoped_drop_is_within_retuned_tolerance():
    baseline_acs = 100.0
    current_acs = compute_acs(total_dependencies=200, total_violations=1)  # 99.5
    assert is_rule_regression(current_acs, baseline_acs, tolerance=5.0) is False