#!/usr/bin/env python3
"""
Runs the golden-PR fixtures (tests/eval/fixtures.py) through the real
compiled graph against a REAL LLM and reports precision/recall/F1 per
fixture and overall.

This is deliberately NOT a pytest test and does NOT run in CI: it needs a
live LLM_API_KEY and makes real network calls to whatever provider
app/config.py's Settings point at, so its output depends on model
behavior that changes over time — the opposite of what CI needs to be
deterministic. tests/eval/test_golden_eval_harness.py is the CI-safe
counterpart: it proves the scoring math in this script is correct using
synthetic data, so this script is trustworthy the moment someone runs it
against a real model. This is the harness the CTO audit's "review quality
is still entirely unmeasured" finding calls for — running it, and
watching the trend over time as fixtures are added, is the actual answer
to that finding, not a claim this file makes on its own.

Usage:
    LLM_API_KEY=... python scripts/run_golden_eval.py

Exits non-zero if overall F1 across all fixtures falls below MIN_F1, so
this can be wired into a release gate once there's enough fixture
coverage to trust the threshold — not wired in yet, on purpose: gating a
release on a single-digit fixture count would be more noise than signal.
"""
import asyncio
import sys

from app.graph.nodes.agent_1_gate import agent_1_gate
from app.graph.nodes.agent_2a_struct import agent_2a_struct
from app.graph.nodes.agent_2b_chaos import agent_2b_chaos
from app.graph.nodes.agent_2c_security import agent_2c_security
from app.graph.nodes.agent_3_critic import agent_3_critic
from app.graph.state import ReviewState
from tests.eval.fixtures import GoldenPR, GOLDEN_PRS
from tests.eval.metrics import EvalResult, score_findings

MIN_F1 = 0.6  # advisory threshold; see module docstring on why it isn't a hard CI gate yet


async def _run_one(pr: GoldenPR) -> EvalResult:
    state = ReviewState(
        repo_full_name="acme/eval",
        pr_number=0,
        installation_id=0,
        diff_text=pr.diff_text,
        ast_payload=pr.ast_payload,
    )

    # Runs the same node sequence the compiled graph would for a
    # non-rejected, non-retry PR, without needing a live GitHub
    # installation (agent_1_gate's diff_fetcher is injected here instead)
    # or a live Supabase baseline (there is deliberately no ledger entry
    # for "acme/eval", so is_rule_regression short-circuits on "no
    # baseline" rather than this eval run depending on persisted state).
    gate_result = agent_1_gate(state, diff_fetcher=lambda s: pr.diff_text)
    state = state.model_copy(update=gate_result)
    if state.hard_rule_violation:
        return score_findings(pr.expected_findings, [])

    a, b, c = await asyncio.gather(
        agent_2a_struct(state), agent_2b_chaos(state), agent_2c_security(state)
    )
    state = state.model_copy(update={"findings": a["findings"] + b["findings"] + c["findings"]})

    critic_result = await agent_3_critic(state)
    return score_findings(pr.expected_findings, critic_result["verified_findings"])


async def main() -> int:
    results: dict[str, EvalResult] = {}
    for pr in GOLDEN_PRS:
        results[pr.name] = await _run_one(pr)

    total_tp = sum(r.true_positives for r in results.values())
    total_fp = sum(r.false_positives for r in results.values())
    total_fn = sum(r.false_negatives for r in results.values())
    overall = EvalResult(true_positives=total_tp, false_positives=total_fp, false_negatives=total_fn)

    print(f"{'fixture':<45} {'precision':>10} {'recall':>10} {'f1':>10}")
    for name, r in results.items():
        print(f"{name:<45} {r.precision:>10.2f} {r.recall:>10.2f} {r.f1:>10.2f}")
    print("-" * 77)
    print(f"{'OVERALL':<45} {overall.precision:>10.2f} {overall.recall:>10.2f} {overall.f1:>10.2f}")

    if overall.f1 < MIN_F1:
        print(f"\nOverall F1 {overall.f1:.2f} is below the advisory threshold {MIN_F1}.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
