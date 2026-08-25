"""
Proves the golden-PR eval harness's scoring math is correct — independent
of whether anyone has pointed it at a real model yet (that requires a live
LLM_API_KEY and is scripts/run_golden_eval.py's job, not this suite's;
see that script's docstring for why it can't run in CI as-is). This test
runs in CI with everything else and guarantees the harness is trustworthy
the moment someone does run it for real.
"""
from app.graph.state import Finding
from tests.eval.fixtures import GOLDEN_PRS
from tests.eval.metrics import ExpectedFinding, score_findings


def test_exact_match_is_a_true_positive():
    expected = [ExpectedFinding(file_path="a.ts", severity="high", description_contains="layer")]
    actual = [Finding(agent="agent_2a_struct", file_path="a.ts", description="disallowed layer crossing", severity="high")]
    result = score_findings(expected, actual)
    assert result.true_positives == 1
    assert result.false_positives == 0
    assert result.false_negatives == 0
    assert result.precision == 1.0
    assert result.recall == 1.0


def test_missed_expected_finding_is_a_false_negative():
    expected = [ExpectedFinding(file_path="a.ts", severity="high", description_contains="layer")]
    actual: list[Finding] = []
    result = score_findings(expected, actual)
    assert result.false_negatives == 1
    assert result.recall == 0.0


def test_unexpected_finding_is_a_false_positive():
    expected: list[ExpectedFinding] = []
    actual = [Finding(agent="agent_2a_struct", file_path="a.ts", description="noise", severity="low")]
    result = score_findings(expected, actual)
    assert result.false_positives == 1
    assert result.precision == 0.0


def test_wrong_severity_does_not_count_as_a_match():
    expected = [ExpectedFinding(file_path="a.ts", severity="high", description_contains="layer")]
    actual = [Finding(agent="agent_2a_struct", file_path="a.ts", description="layer crossing", severity="low")]
    result = score_findings(expected, actual)
    assert result.true_positives == 0
    assert result.false_positives == 1
    assert result.false_negatives == 1


def test_duplicate_actual_findings_do_not_double_satisfy_one_expectation():
    expected = [ExpectedFinding(file_path="a.ts", severity="high", description_contains="layer")]
    actual = [
        Finding(agent="agent_2a_struct", file_path="a.ts", description="layer crossing", severity="high"),
        Finding(agent="agent_2a_struct", file_path="a.ts", description="layer crossing again", severity="high"),
    ]
    result = score_findings(expected, actual)
    # One true positive (the expectation is satisfied once), one leftover
    # actual finding counted as a false positive — greedy one-to-one
    # matching, not "any actual finding resembling this expectation".
    assert result.true_positives == 1
    assert result.false_positives == 1


def test_perfect_empty_match_scores_perfectly():
    # A fixture that expects nothing, and gets nothing, shouldn't be
    # penalized by a precision/recall formula that divides by zero.
    result = score_findings([], [])
    assert result.precision == 1.0
    assert result.recall == 1.0
    assert result.f1 == 1.0


def test_golden_pr_fixtures_are_well_formed():
    # Guards the fixture file itself, not the scoring math — a fixture
    # with an empty name or a malformed AST payload would silently produce
    # a meaningless eval run rather than an obvious error.
    assert len(GOLDEN_PRS) > 0
    names = [pr.name for pr in GOLDEN_PRS]
    assert len(names) == len(set(names)), "golden PR fixture names must be unique"
    for pr in GOLDEN_PRS:
        assert pr.diff_text.strip()
        assert pr.ast_payload.changed_files
