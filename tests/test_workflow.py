"""
Graph-wiring coverage for the narrow hallucination-retry edge (Critic ->
Agent 2A only, see workflow.py/routing.py). Runs the real compiled graph
with every agent node mocked so these are true call-count assertions on
the wiring itself, not on any one node's internal logic (agent_3_critic's
verification/tiering logic already has its own coverage in
test_agent_3_critic.py).

Before this change, the retry edge went agent_3_critic -> agent_1_gate,
which fanned back out to ALL THREE specialists every retry — so a
hallucination-triggered retry re-spent an LLM call on agent_2b_chaos and
agent_2c_security even though neither of them was what hallucinated. The
narrow edge fixes that: only agent_2a_struct gets re-invoked.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import get_settings
from app.graph.state import Finding, ReviewState
from app.graph.workflow import build_graph
from app.schemas.ast_payload import ASTAnalyzerPayload


def _ast_payload() -> ASTAnalyzerPayload:
    # No symbols/edges at all — any symbol_ref agent_2a_struct names will
    # always fail exact AND near-miss verification, so it hallucinates on
    # every pass, driving the retry loop all the way to the cap.
    return ASTAnalyzerPayload(
        repo_full_name="acme/widgets", pr_number=1, changed_files=[], symbols=[], dependency_graph=[],
    )


def _initial_state() -> ReviewState:
    return ReviewState(
        repo_full_name="acme/widgets", pr_number=1, installation_id=12345, ast_payload=_ast_payload(),
    )


def _patch_critic_dependencies(monkeypatch):
    monkeypatch.setattr(
        "app.graph.nodes.agent_3_critic.LedgerRepository",
        lambda: MagicMock(get_baseline=lambda repo: None, get_consecutive_rejections=lambda pattern_key: 0),
    )
    monkeypatch.setattr(
        "app.graph.nodes.agent_3_critic.VectorStore",
        lambda: MagicMock(record_incident=AsyncMock()),
    )
    monkeypatch.setattr("pathlib.Path.read_text", lambda self: "{verified_findings}")


def _install_counting_mocks(monkeypatch):
    """
    Replaces agent_1_gate/2a/2b/2c in workflow.py's own namespace (what
    build_graph() actually wires into the graph) with counting stand-ins.
    agent_2a_struct always returns an unverifiable finding, so the retry
    loop runs to the cap; agent_2b_chaos returns one real critical finding
    (no ref, so it's never touched by verification) purely so the run ends
    at pause_for_human_approval instead of finalize_and_post — keeping
    this test from having to also stub out agent_4_autofix/GitHubClient.
    """
    call_counts = {"agent_1_gate": 0, "agent_2a_struct": 0, "agent_2b_chaos": 0, "agent_2c_security": 0}

    async def fake_gate(state):
        call_counts["agent_1_gate"] += 1
        return {"hard_rule_violation": False}

    async def fake_2a(state):
        call_counts["agent_2a_struct"] += 1
        return {
            "findings": [
                Finding(
                    agent="agent_2a_struct", file_path="a.ts", description="fake",
                    severity="low", symbol_ref="ghost",
                )
            ]
        }

    async def fake_2b(state):
        call_counts["agent_2b_chaos"] += 1
        return {
            "findings": [
                Finding(agent="agent_2b_chaos", file_path="b.ts", description="real issue", severity="critical")
            ]
        }

    async def fake_2c(state):
        call_counts["agent_2c_security"] += 1
        return {"findings": []}

    monkeypatch.setattr("app.graph.workflow.agent_1_gate", fake_gate)
    monkeypatch.setattr("app.graph.workflow.agent_2a_struct", fake_2a)
    monkeypatch.setattr("app.graph.workflow.agent_2b_chaos", fake_2b)
    monkeypatch.setattr("app.graph.workflow.agent_2c_security", fake_2c)

    return call_counts


@pytest.mark.asyncio
async def test_retry_does_not_reinvoke_agent_2b_or_agent_2c(monkeypatch):
    _patch_critic_dependencies(monkeypatch)
    call_counts = _install_counting_mocks(monkeypatch)

    graph = build_graph()

    with patch(
        "app.graph.nodes.agent_3_critic.get_llm_client",
        return_value=MagicMock(complete=AsyncMock(return_value="narrative")),
    ):
        await graph.ainvoke(_initial_state())

    # agent_2a_struct hallucinates every pass, so it keeps getting retried
    # until the cap is reached (route_after_critic checks the POST-
    # increment count against the cap, so `cap` total passes — see
    # test_routing.py's test_route_after_critic_stops_retrying_once_cap_reached)
    # — but 2b/2c only ever run ONCE, on the initial fan-out, never again
    # on any retry.
    cap = get_settings().hallucination_retry_cap
    assert call_counts["agent_1_gate"] == 1
    assert call_counts["agent_2a_struct"] == cap
    assert call_counts["agent_2b_chaos"] == 1
    assert call_counts["agent_2c_security"] == 1


@pytest.mark.asyncio
async def test_retry_cap_is_enforced_on_the_narrow_edge(monkeypatch):
    _patch_critic_dependencies(monkeypatch)
    call_counts = _install_counting_mocks(monkeypatch)

    graph = build_graph()

    with patch(
        "app.graph.nodes.agent_3_critic.get_llm_client",
        return_value=MagicMock(complete=AsyncMock(return_value="narrative")),
    ):
        await graph.ainvoke(_initial_state())

    # A permanently-hallucinating agent_2a_struct must not loop forever —
    # exactly `cap` total passes, then the graph gives up and routes onward.
    cap = get_settings().hallucination_retry_cap
    assert call_counts["agent_2a_struct"] == cap


@pytest.mark.asyncio
async def test_narrow_retry_edge_cuts_specialist_calls_versus_the_old_full_fanout(monkeypatch):
    """
    Cost check: under the old agent_3_critic -> agent_1_gate retry edge,
    every retry re-ran the full fan-out, so a run that takes `cap` total
    passes to resolve cost `cap` calls to EACH of agent_2a_struct,
    agent_2b_chaos, and agent_2c_security — cap * 3 specialist calls
    total. The narrow edge costs `cap` calls to agent_2a_struct alone,
    plus exactly 1 each to 2b/2c: cap + 2 total. For the default cap (3),
    that's 9 calls under the old wiring vs. 5 under the new one — roughly
    the ~3x reduction, growing sharper as the cap increases.
    """
    _patch_critic_dependencies(monkeypatch)
    call_counts = _install_counting_mocks(monkeypatch)

    graph = build_graph()

    with patch(
        "app.graph.nodes.agent_3_critic.get_llm_client",
        return_value=MagicMock(complete=AsyncMock(return_value="narrative")),
    ):
        await graph.ainvoke(_initial_state())

    cap = get_settings().hallucination_retry_cap
    old_wiring_specialist_calls = cap * 3
    new_wiring_specialist_calls = sum(call_counts[a] for a in ("agent_2a_struct", "agent_2b_chaos", "agent_2c_security"))
    assert new_wiring_specialist_calls < old_wiring_specialist_calls
    assert new_wiring_specialist_calls == cap + 2
