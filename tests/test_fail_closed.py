"""
Audit P0-1: an LLM failure must never be rendered as a clean pass.

Covers the links in the old fail-open chain: the retry predicate
(non-retryable 4xx), empty/non-JSON completions, agents swallowing errors
into [], the Critic rendering "No findings. Clean pass." for an empty list,
the health check staying green for a decommissioned model, and the
pipeline recording an incomplete review as if it were clean.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from groq import BadRequestError, RateLimitError

from app.config import Settings
from app.graph.nodes.agent_2a_struct import agent_2a_struct
from app.graph.nodes.agent_2b_chaos import agent_2b_chaos
from app.graph.nodes.agent_2c_security import agent_2c_security
from app.graph.nodes.agent_3_critic import _render_markdown, agent_3_critic
from app.graph.state import Finding, ReviewState
from app.schemas.ast_payload import ASTAnalyzerPayload, PackageRef
from app.services.finding_parser import parse_findings_json
from app.services.llm_client import LLMClient


def _state(**kw) -> ReviewState:
    payload = ASTAnalyzerPayload(
        repo_full_name="acme/widgets", pr_number=1, changed_files=["src/a.ts"], symbols=[], dependency_graph=[],
        changed_packages=kw.pop("changed_packages", []),
    )
    return ReviewState(repo_full_name="acme/widgets", pr_number=1, installation_id=1, ast_payload=payload, **kw)


def _status_error(cls, code: int):
    req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    return cls("err", response=httpx.Response(code, request=req), body=None)


def _completion(content):
    return MagicMock(choices=[MagicMock(message=MagicMock(content=content))], usage=None)


@pytest.mark.asyncio
async def test_non_retryable_400_is_not_retried():
    client = LLMClient()
    create = AsyncMock(side_effect=_status_error(BadRequestError, 400))
    client._client = MagicMock(chat=MagicMock(completions=MagicMock(create=create)))
    with pytest.raises(BadRequestError):
        await client.complete("p")
    assert create.await_count == 1  # previously 4 attempts, ~14s of backoff


@pytest.mark.asyncio
async def test_429_is_retried():
    client = LLMClient()
    create = AsyncMock(side_effect=[_status_error(RateLimitError, 429), _completion('{"findings": []}')])
    client._client = MagicMock(chat=MagicMock(completions=MagicMock(create=create)))
    with patch("asyncio.sleep", new=AsyncMock()):
        assert await client.complete("p") == '{"findings": []}'
    assert create.await_count == 2


@pytest.mark.asyncio
async def test_reasoning_effort_comes_from_settings_not_hardcoded():
    client = LLMClient()
    client._reasoning_effort = None
    create = AsyncMock(return_value=_completion("{}"))
    client._client = MagicMock(chat=MagicMock(completions=MagicMock(create=create)))
    await client.complete("p")
    assert "reasoning_effort" not in create.await_args.kwargs


@pytest.mark.asyncio
async def test_empty_completion_raises_instead_of_returning_nothing():
    client = LLMClient()
    create = AsyncMock(return_value=_completion(""))
    client._client = MagicMock(chat=MagicMock(completions=MagicMock(create=create)))
    with pytest.raises(Exception) as exc_info:
        await client.complete("p", agent_name="agent_2a_struct")
    assert "empty completion" in str(exc_info.value)


def test_default_model_is_live_and_reasoning_effort_is_a_setting(monkeypatch):
    for name in ("LLM_PROVIDER", "LLM_MODEL_NAME", "LLM_REASONING_EFFORT"):
        monkeypatch.delenv(name, raising=False)
    s = Settings()
    assert s.llm_provider == "groq"
    assert s.llm_model_name == "openai/gpt-oss-120b"
    assert s.llm_reasoning_effort == "low"
    assert Settings(llm_reasoning_effort="").llm_reasoning_effort == ""


def test_non_json_response_raises_instead_of_returning_empty():
    with pytest.raises(ValueError) as exc_info:  # FindingsParseError is a ValueError
        parse_findings_json("I could not review this.", agent_name="agent_2a_struct")
    assert type(exc_info.value).__name__ == "FindingsParseError"


@pytest.mark.asyncio
async def test_agent_errors_are_reported_not_swallowed():
    failing = MagicMock(complete=AsyncMock(side_effect=RuntimeError("model_decommissioned")))
    with patch("app.graph.nodes.agent_2a_struct.get_llm_client", return_value=failing):
        out = await agent_2a_struct(_state())
    assert out == {"findings": [], "agent_errors": ["agent_2a_struct"]}

    vs = MagicMock(similar_incidents=AsyncMock(return_value=[]))
    with patch("app.graph.nodes.agent_2b_chaos.get_llm_client", return_value=failing), \
         patch("app.graph.nodes.agent_2b_chaos.VectorStore", return_value=vs):
        out = await agent_2b_chaos(_state())
    assert out["agent_errors"] == ["agent_2b_chaos"]


@pytest.mark.asyncio
async def test_agent_2c_keeps_deterministic_findings_when_llm_phase_fails(monkeypatch):
    osv_hit = Finding(agent="agent_2c_security", file_path="package.json",
                      description="Known vulnerability in evil@1.0.0", severity="high")
    monkeypatch.setattr("app.graph.nodes.agent_2c_security._phase1_deterministic_registry_check",
                        AsyncMock(return_value=[osv_hit]))
    monkeypatch.setattr("app.graph.nodes.agent_2c_security._fetch_publish_age_days",
                        AsyncMock(return_value=900.0))
    failing = MagicMock(complete=AsyncMock(side_effect=RuntimeError("model_decommissioned")))
    monkeypatch.setattr("app.graph.nodes.agent_2c_security.get_llm_client", lambda: failing)
    out = await agent_2c_security(_state(changed_packages=[PackageRef(name="evil", version="1.0.0")]))
    assert [f.description for f in out["findings"]] == ["Known vulnerability in evil@1.0.0"]
    assert out["agent_errors"] == ["agent_2c_security"]


@pytest.mark.asyncio
async def test_critic_never_renders_clean_pass_when_an_agent_failed():
    ledger = MagicMock(get_baseline=MagicMock(return_value={"acs_score": 100.0}),
                       get_consecutive_rejections=MagicMock(return_value=0))
    with patch("app.graph.nodes.agent_3_critic.LedgerRepository", return_value=ledger), \
         patch("app.graph.nodes.agent_3_critic._record_incidents", new=AsyncMock()):
        out = await agent_3_critic(_state(agent_errors=["agent_2a_struct", "agent_2b_chaos"]))
    md = out["final_comment_markdown"]
    assert out["review_incomplete"] is True
    assert "Review incomplete" in md and "Clean pass" not in md
    assert out["acs_score"] is None  # 2A down -> ACS unknowable, not 100


def test_regression_with_no_findings_is_not_called_clean():
    md = _render_markdown([], 40.0, True, None)
    assert "regression" in md.lower() and "Clean pass" not in md and "No findings." not in md


@pytest.mark.asyncio
async def test_llm_health_check_fails_when_configured_model_is_gone():
    from app.services import health_checks

    def fake_llm(model_ids):
        models = MagicMock(data=[MagicMock(id=m) for m in model_ids])
        return MagicMock(model="openai/gpt-oss-120b",
                         raw_client=MagicMock(models=MagicMock(list=AsyncMock(return_value=models))))

    with patch.object(health_checks, "get_llm_client", return_value=fake_llm(["llama-3.3-70b-versatile"])):
        gone = await health_checks.check_llm_provider()
    with patch.object(health_checks, "get_llm_client", return_value=fake_llm(["openai/gpt-oss-120b"])):
        present = await health_checks.check_llm_provider()
    assert gone["status"] == "unhealthy" and "not offered" in gone["error"]
    assert present["status"] == "healthy"
