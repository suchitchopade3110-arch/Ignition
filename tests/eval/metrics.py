"""
Precision/recall scoring for the golden-PR eval harness.

Kept separate from the fixtures and the runner so the scoring math itself
is unit-testable without a graph run or an LLM in the loop — see
test_golden_eval_harness.py, which proves this module is correct using
synthetic data, independent of whether anyone has actually pointed the
harness at a real model yet.
"""
from dataclasses import dataclass

from app.graph.state import Finding


@dataclass(frozen=True)
class ExpectedFinding:
    """
    One hand-labeled finding a golden-PR fixture expects the graph to
    surface. Matching an actual Finding is deliberately loose — file_path
    + severity + a required substring in the description — rather than an
    exact string match, since an LLM will never phrase a description
    identically to the fixture's expectation, and pinning that would make
    the fixture unmaintainable rather than making the eval more honest.
    """
    file_path: str
    severity: str
    description_contains: str  # case-insensitive substring match


@dataclass(frozen=True)
class EvalResult:
    true_positives: int
    false_positives: int
    false_negatives: int

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom else 1.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom else 1.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


def _matches(expected: ExpectedFinding, actual: Finding) -> bool:
    return (
        expected.file_path == actual.file_path
        and expected.severity == actual.severity
        and expected.description_contains.lower() in actual.description.lower()
    )


def score_findings(expected: list[ExpectedFinding], actual: list[Finding]) -> EvalResult:
    """
    Greedy one-to-one matching: each expected finding claims at most one
    actual finding (and vice versa), so a fixture expecting one finding
    can't be "satisfied" twice by the model emitting duplicates.
    """
    unclaimed_actual = list(actual)
    true_positives = 0
    for exp in expected:
        match = next((a for a in unclaimed_actual if _matches(exp, a)), None)
        if match is not None:
            unclaimed_actual.remove(match)
            true_positives += 1

    false_negatives = len(expected) - true_positives
    false_positives = len(unclaimed_actual)
    return EvalResult(
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
    )
