"""
Coverage for agent_2a_struct's rejected-claims re-prompt (Phase 2 of the
narrow retry loop): on a retry, agent_3_critic threads the refs that
failed verification last pass into state.rejected_claims, and this agent
must surface them in its own prompt so it doesn't just guess the same
ones again.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.graph.nodes.agent_2a_struct import _format_rejected_claims, agent_2a_struct
from app.graph.state import ReviewState, RejectedClaim
from app.schemas.ast_payload import ASTAnalyzerPayload


def _ast_payload() -> ASTAnalyzerPayload:
    return ASTAnalyzerPayload(
        repo_full_name="acme/widgets", pr_number=1, changed_files=[], symbols=[], dependency_graph=[],
    )


def _state(**overrides) -> ReviewState:
    defaults = dict(
        repo_full_name="acme/widgets", pr_number=1, installation_id=12345, ast_payload=_ast_payload(),
    )
    defaults.update(overrides)
    return ReviewState(**defaults)


class TestFormatRejectedClaims:
    def test_empty_on_a_first_pass(self):
        assert _format_rejected_claims(_state()) == ""

    def test_includes_rejected_symbol_ref(self):
        state = _state(rejected_claims=[RejectedClaim(symbol_ref="ghost", description="fake finding")])
        rendered = _format_rejected_claims(state)
        assert "ghost" in rendered
        assert "fake finding" in rendered
        assert "did NOT verify" in rendered

    def test_includes_rejected_dependency_edge_ref(self):
        state = _state(
            rejected_claims=[
                RejectedClaim(dependency_edge_ref=("a.ts", "b.ts"), description="bad layering claim"),
            ]
        )
        rendered = _format_rejected_claims(state)
        assert "a.ts" in rendered and "b.ts" in rendered
        assert "bad layering claim" in rendered


class TestAgentTwoAPromptWiring:
    @pytest.mark.asyncio
    async def test_rejected_claims_are_passed_into_the_prompt(self, monkeypatch):
        state = _state(rejected_claims=[RejectedClaim(symbol_ref="ghost", description="fake finding")])

        captured = {}

        class FakeTemplate(str):
            def format(self, **kwargs):
                captured.update(kwargs)
                return "prompt"

        monkeypatch.setattr("pathlib.Path.read_text", lambda self: FakeTemplate())

        with patch(
            "app.graph.nodes.agent_2a_struct.get_llm_client",
            return_value=MagicMock(complete=AsyncMock(return_value='{"findings": []}')),
        ):
            await agent_2a_struct(state)

        assert "ghost" in captured["rejected_claims"]
        assert "fake finding" in captured["rejected_claims"]

    @pytest.mark.asyncio
    async def test_no_rejected_claims_yields_empty_prompt_section(self, monkeypatch):
        state = _state()

        captured = {}

        class FakeTemplate(str):
            def format(self, **kwargs):
                captured.update(kwargs)
                return "prompt"

        monkeypatch.setattr("pathlib.Path.read_text", lambda self: FakeTemplate())

        with patch(
            "app.graph.nodes.agent_2a_struct.get_llm_client",
            return_value=MagicMock(complete=AsyncMock(return_value='{"findings": []}')),
        ):
            await agent_2a_struct(state)

        assert captured["rejected_claims"] == ""
