from app.graph.scoring import compute_acs, is_rule_regression


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