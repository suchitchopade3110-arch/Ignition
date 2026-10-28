"""
Audit P1-5: repo settings were saved but never applied. run_review_job now
loads them first and puts them on the graph state; routing reads them:
  - AI review off   -> nothing runs; the check run concludes neutral
  - scans off       -> those specialists don't run (all off: straight to the Critic)
  - HITL off        -> finalize_and_post even for a critical review
  - auto-fix off    -> agent_4_autofix is skipped
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.graph.workflow as workflow
from app.graph.state import Finding, ReviewState
from app.schemas.ast_payload import ASTAnalyzerPayload
from app.services.ast_client import ASTClient
from app.services.review_pipeline import run_review_job
from tests.test_check_runs import _enqueue
from tests.test_integration_webhook_review_comment import (  # noqa: F401  (fixtures)
    fake_repos, mock_arq, mock_externals,
)

SPECIALISTS = ["agent_2a_struct", "agent_2b_chaos", "agent_2c_security"]


@pytest.fixture
def recorded(monkeypatch):
    """Every node in workflow.py's namespace replaced by a recorder."""
    calls: list[str] = []
    critic_severity = {"value": "none"}

    def recorder(name, result):
        async def node(state):
            calls.append(name)
            return result(state) if callable(result) else result
        return node

    monkeypatch.setattr(workflow, "agent_1_gate", recorder("agent_1_gate", {"hard_rule_violation": False}))
    for name in SPECIALISTS:
        monkeypatch.setattr(workflow, name, recorder(name, {"findings": []}))
    monkeypatch.setattr(workflow, "agent_3_critic", recorder("agent_3_critic", lambda s: {
        "hitl_severity": critic_severity["value"], "critic_wants_retry": False,
        "verified_findings": [Finding(agent="agent_2b_chaos", file_path="a.ts", description="d",
                                      severity=critic_severity["value"])],
        "final_comment_markdown": f"- `[{critic_severity['value'].upper()}]` a.ts: d"}))
    monkeypatch.setattr(workflow, "agent_4_autofix", recorder("agent_4_autofix", {"autofix_posted": 0, "autofix_failed": 0}))
    monkeypatch.setattr(workflow, "pause_for_human_approval", recorder("pause_for_human_approval", {}))
    monkeypatch.setattr(workflow, "finalize_and_post", recorder("finalize_and_post", {}))
    return calls, critic_severity


def _state(**flags) -> ReviewState:
    payload = ASTAnalyzerPayload(repo_full_name="acme/widgets", pr_number=1, changed_files=[], symbols=[],
                                 dependency_graph=[])
    return ReviewState(repo_full_name="acme/widgets", pr_number=1, installation_id=1, ast_payload=payload, **flags)


async def _run(state):
    await workflow.build_graph().ainvoke(state)


@pytest.mark.asyncio
async def test_a_disabled_scan_does_not_run(recorded):
    calls, _ = recorded
    await _run(_state(enabled_agents=["agent_2a_struct", "agent_2b_chaos"]))
    assert "agent_2c_security" not in calls
    assert {"agent_2a_struct", "agent_2b_chaos", "agent_3_critic"} <= set(calls)


@pytest.mark.asyncio
async def test_no_scans_goes_straight_to_the_critic(recorded):
    calls, _ = recorded
    await _run(_state(enabled_agents=[]))
    assert not set(SPECIALISTS) & set(calls)
    assert calls[:2] == ["agent_1_gate", "agent_3_critic"]


@pytest.mark.asyncio
async def test_hitl_off_finalizes_a_critical_review(recorded):
    calls, severity = recorded
    severity["value"] = "critical"
    await _run(_state(enable_hitl=False))
    # Auto-fix is on by default and now runs after the summary (solutions
    # doc, P2 partial success).
    assert "pause_for_human_approval" not in calls and calls[-2:] == ["finalize_and_post", "agent_4_autofix"]


@pytest.mark.asyncio
async def test_hitl_on_still_pauses_a_critical_review(recorded):
    calls, severity = recorded
    severity["value"] = "critical"
    await _run(_state(enable_hitl=True))
    assert calls[-1] == "pause_for_human_approval" and "finalize_and_post" not in calls


@pytest.mark.asyncio
async def test_auto_fix_off_skips_agent_4(recorded):
    calls, _ = recorded
    await _run(_state(enable_auto_fix=False))
    assert "agent_4_autofix" not in calls and calls[-1] == "finalize_and_post"


@pytest.mark.asyncio
async def test_auto_fix_on_runs_agent_4(recorded):
    calls, _ = recorded
    await _run(_state(enable_auto_fix=True))
    # Summary first, then suggestions (solutions doc, P2 partial success).
    assert calls[-2:] == ["finalize_and_post", "agent_4_autofix"]


# --- the job loads the settings and maps them onto the state --------------------

@pytest.mark.asyncio
async def test_ai_review_off_runs_nothing_and_concludes_neutral(fake_repos, mock_externals, mock_arq):
    fake_review_repo, fake_repo_repo = fake_repos
    fake_repo_repo.settings["enable_ai_review"] = False
    event_payload, review_id, correlation_id = await _enqueue(mock_arq)
    await run_review_job({}, event_payload, review_id, correlation_id)
    # Loaded by GitHub's numeric repository id (P2 repo IDs), not owner_name.
    assert fake_repo_repo.settings_requests == [1001]
    ASTClient.analyze_git.assert_not_awaited()
    gh = mock_externals["github_instance"]
    kwargs = gh.complete_check_run.call_args.kwargs
    assert (kwargs["conclusion"], kwargs["title"]) == ("neutral", "AI review disabled for this repo")
    assert fake_review_repo.rows[review_id]["status"] == "completed"
    gh.upsert_sticky_comment.assert_not_called()


@pytest.mark.asyncio
async def test_settings_reach_the_graph_state(fake_repos, mock_externals, mock_arq, monkeypatch):
    fake_review_repo, fake_repo_repo = fake_repos
    fake_repo_repo.settings.update(security_scan=False, enable_hitl=False, enable_auto_fix=True)
    seen = {}
    import app.services.review_pipeline as pipeline
    real_astream = pipeline.graph.astream

    def spy(state, *a, **kw):
        seen.update(enabled_agents=state.enabled_agents, enable_hitl=state.enable_hitl,
                    enable_auto_fix=state.enable_auto_fix)
        return real_astream(state, *a, **kw)
    monkeypatch.setattr(pipeline.graph, "astream", spy)
    event_payload, review_id, correlation_id = await _enqueue(mock_arq)
    await run_review_job({}, event_payload, review_id, correlation_id)
    assert seen == {"enabled_agents": ["agent_2a_struct", "agent_2b_chaos"], "enable_hitl": False,
                    "enable_auto_fix": True}
    # The dashboard's agent timeline has no row for a scan that is off.
    agent_ids = [a["id"] for a in fake_review_repo.rows[review_id]["agents"]]
    assert "agent_2c_security" not in agent_ids and "agent_2b_chaos" in agent_ids


@pytest.mark.asyncio
async def test_unreadable_settings_fail_closed(fake_repos, mock_externals, mock_arq, monkeypatch):
    fake_review_repo, fake_repo_repo = fake_repos

    def broken(repo_id, repo_full_name=None):
        raise RuntimeError("supabase down")
    monkeypatch.setattr("app.services.review_pipeline.repo_repo.get_or_create_settings", broken)
    event_payload, review_id, correlation_id = await _enqueue(mock_arq)
    await run_review_job({}, event_payload, review_id, correlation_id)
    ASTClient.analyze_git.assert_not_awaited()  # never review a repo whose owner may have turned it off
    row = fake_review_repo.rows[review_id]
    assert row["status"] == "failed" and "settings" in row["status_reason"]
    kwargs = mock_externals["github_instance"].complete_check_run.call_args.kwargs
    assert kwargs["conclusion"] == "neutral" and kwargs["title"].startswith("Ignition could not finish")


@pytest.mark.asyncio
async def test_acs_is_not_reported_when_the_architecture_scan_is_off(monkeypatch):
    # ACS counts Agent 2A's findings; with 2A switched off a "100" would be
    # a made-up perfect score (and would feed regression baselines).
    from unittest.mock import patch
    from app.graph.nodes import agent_3_critic as critic
    from app.schemas.ast_payload import DependencyEdge
    monkeypatch.setattr(critic, "LedgerRepository", lambda: MagicMock(
        get_baseline=lambda repo: {"acs_score": 100.0}, get_consecutive_rejections=lambda p, r: 0))
    monkeypatch.setattr(critic, "VectorStore", lambda: MagicMock(record_incident=AsyncMock()))
    payload = ASTAnalyzerPayload(repo_full_name="acme/widgets", pr_number=1, changed_files=["a"], symbols=[],
                                 dependency_graph=[DependencyEdge(from_file="a", to_file="b", imported_symbols=[])])
    state = ReviewState(repo_full_name="acme/widgets", pr_number=1, installation_id=1, ast_payload=payload,
                        enabled_agents=["agent_2b_chaos", "agent_2c_security"])
    with patch.object(critic, "get_llm_client", return_value=MagicMock(complete=AsyncMock(return_value="n"))):
        result = await critic.agent_3_critic(state)
    assert result["acs_score"] is None and result["is_regression"] is False
    assert "ACS: n/a" in result["final_comment_markdown"]
