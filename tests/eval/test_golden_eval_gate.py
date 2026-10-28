"""
scripts/run_golden_eval.py must keep rejecting its two hard-gate fixtures
in agent_1_gate alone, before any LLM-backed agent runs. After P1-9 the
gate trusts the analyzer's hard_rule_violations instead of substring-
scanning the diff, so the eval fixture has to carry what the analyzer
reports for its added eval() line, and the script must call the gate
without the removed diff_fetcher argument.
"""
import importlib.util
from pathlib import Path

import pytest

from tests.eval.fixtures import GOLDEN_PRS

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "run_golden_eval.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("run_golden_eval", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_hard_gate_fixtures_short_circuit_before_any_agent(monkeypatch):
    script = _load_script()

    async def agent_must_not_run(state):
        raise AssertionError("an LLM agent ran for a fixture the gate should have rejected")

    for name in ("agent_2a_struct", "agent_2b_chaos", "agent_2c_security"):
        monkeypatch.setattr(script, name, agent_must_not_run)

    gate_fixtures = [pr for pr in GOLDEN_PRS if pr.name.startswith("hard_gate_")]
    assert len(gate_fixtures) == 2
    for pr in gate_fixtures:
        result = await script._run_one(pr)
        assert (result.false_positives, result.false_negatives) == (0, 0), pr.name
