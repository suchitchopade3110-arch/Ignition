"""
P0-2 follow-up: golden fixtures carried hand-written changed_files and AST
payloads, so the eval never exercised what the analyzer really reports.
The fixtures named below are regenerated from real analyzer output
(ast-analyzer/scripts/golden-fixtures.ts builds each as a two-commit git
repo and runs analyzePullRequest on it). Their diff_text is the real
`git diff`, and their payload is the analyzer's JSON, loaded from
tests/eval/real/. ast-analyzer/golden-fixtures.test.ts re-runs the
generator and fails if the committed JSON drifts.
"""
import json
from pathlib import Path

import pytest

from app.schemas.ast_payload import ASTAnalyzerPayload
from tests.eval.fixtures import GOLDEN_PRS

REAL = Path(__file__).resolve().parent / "real"
REGENERATED = [
    "layer_crossing_repository_to_http_client",
    "hard_gate_rejects_eval_call_in_added_code",
    "off_by_one_in_pagination_slice",
]


@pytest.mark.parametrize("name", REGENERATED)
def test_fixture_payload_and_diff_come_from_the_real_analyzer(name):
    recorded = json.loads((REAL / f"{name}.json").read_text())
    assert recorded["generated_by"] == "ast-analyzer/scripts/golden-fixtures.ts"
    [fixture] = [g for g in GOLDEN_PRS if g.name == name]
    assert fixture.diff_text == recorded["diff_text"]
    assert fixture.ast_payload == ASTAnalyzerPayload.model_validate(recorded["ast_payload"])


def test_the_real_eval_fixture_reports_the_hard_rule_the_gate_relies_on():
    [fixture] = [g for g in GOLDEN_PRS if g.name == "hard_gate_rejects_eval_call_in_added_code"]
    assert any("eval" in v for v in fixture.ast_payload.hard_rule_violations)
