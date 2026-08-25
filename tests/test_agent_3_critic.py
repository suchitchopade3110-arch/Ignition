"""
Coverage for the Critic's exact-lookup hallucination verification — this
was previously untested, and the bug that shipped as a result (every
finding skipped verification because nothing ever set the `description`
prefix `_verify_findings` checked for) would have been caught immediately
by a test that plants an unverifiable finding and asserts it gets dropped.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.graph.nodes.agent_3_critic import _verify_findings, agent_3_critic
from app.graph.state import Finding, ReviewState
from app.schemas.ast_payload import ASTAnalyzerPayload, DependencyEdge, SymbolRef


def _ast_payload(symbols=None, dependency_graph=None) -> ASTAnalyzerPayload:
    return ASTAnalyzerPayload(
        repo_full_name="acme/widgets",
        pr_number=1,
        changed_files=[],
        symbols=symbols or [],
        dependency_graph=dependency_graph or [],
    )


def _state(findings: list[Finding], ast_payload: ASTAnalyzerPayload, **overrides) -> ReviewState:
    defaults = dict(
        repo_full_name="acme/widgets",
        pr_number=1,
        installation_id=12345,
        ast_payload=ast_payload,
        findings=findings,
    )
    defaults.update(overrides)
    return ReviewState(**defaults)


class TestVerifyFindings:
    def test_symbol_ref_matching_real_symbol_is_kept(self):
        ast_payload = _ast_payload(
            symbols=[SymbolRef(file_path="a.ts", symbol_name="doThing", kind="function", line=5)]
        )
        finding = Finding(
            agent="agent_2a_struct", file_path="a.ts", description="doThing is unsafe",
            severity="high", symbol_ref="doThing",
        )
        verified, hallucinated_count = _verify_findings(_state([finding], ast_payload))
        assert verified == [finding]
        assert hallucinated_count == 0

    def test_symbol_ref_naming_nonexistent_symbol_is_dropped(self):
        ast_payload = _ast_payload(symbols=[])
        finding = Finding(
            agent="agent_2a_struct", file_path="a.ts", description="madeUpFn is unsafe",
            severity="high", symbol_ref="madeUpFn",
        )
        verified, hallucinated_count = _verify_findings(_state([finding], ast_payload))
        assert verified == []
        assert hallucinated_count == 1

    def test_dependency_edge_ref_matching_real_edge_is_kept(self):
        ast_payload = _ast_payload(
            dependency_graph=[DependencyEdge(from_file="api.ts", to_file="db.ts", imported_symbols=["Client"])]
        )
        finding = Finding(
            agent="agent_2a_struct", file_path="api.ts", description="layer crossing",
            severity="medium", dependency_edge_ref=("api.ts", "db.ts"),
        )
        verified, hallucinated_count = _verify_findings(_state([finding], ast_payload))
        assert verified == [finding]
        assert hallucinated_count == 0

    def test_dependency_edge_ref_naming_nonexistent_edge_is_dropped(self):
        ast_payload = _ast_payload(dependency_graph=[])
        finding = Finding(
            agent="agent_2a_struct", file_path="api.ts", description="layer crossing",
            severity="medium", dependency_edge_ref=("api.ts", "db.ts"),
        )
        verified, hallucinated_count = _verify_findings(_state([finding], ast_payload))
        assert verified == []
        assert hallucinated_count == 1

    def test_finding_with_no_ref_passes_through_unverified(self):
        # Security/supply-chain findings (Agent 2C) have no AST claim to
        # check — they must not be silently dropped just because they
        # carry neither symbol_ref nor dependency_edge_ref.
        ast_payload = _ast_payload()
        finding = Finding(
            agent="agent_2c_security", file_path="package.json",
            description="Known vulnerability in left-pad@1.0.0", severity="high",
        )
        verified, hallucinated_count = _verify_findings(_state([finding], ast_payload))
        assert verified == [finding]
        assert hallucinated_count == 0

    def test_mixed_batch_drops_only_the_hallucinated_one(self):
        ast_payload = _ast_payload(
            symbols=[SymbolRef(file_path="a.ts", symbol_name="real", kind="function", line=1)]
        )
        real = Finding(
            agent="agent_2a_struct", file_path="a.ts", description="ok", severity="low", symbol_ref="real",
        )
        fake = Finding(
            agent="agent_2a_struct", file_path="a.ts", description="fake", severity="low", symbol_ref="fake",
        )
        verified, hallucinated_count = _verify_findings(_state([real, fake], ast_payload))
        assert verified == [real]
        assert hallucinated_count == 1


class TestAgentThreeCriticNode:
    """Full-node behavior: ACS unit consistency, retry-loop wiring, HITL on regression."""

    def _patch_common(self, monkeypatch, baseline_acs=None):
        monkeypatch.setattr(
            "app.graph.nodes.agent_3_critic.LedgerRepository",
            lambda: MagicMock(get_baseline=lambda repo: {"acs_score": baseline_acs} if baseline_acs is not None else None),
        )
        monkeypatch.setattr(
            "app.graph.nodes.agent_3_critic.VectorStore",
            lambda: MagicMock(record_incident=AsyncMock()),
        )
        monkeypatch.setattr(
            "pathlib.Path.read_text", lambda self: "{verified_findings}"
        )

    @pytest.mark.asyncio
    async def test_acs_only_counts_architecture_findings(self, monkeypatch):
        self._patch_common(monkeypatch)
        ast_payload = _ast_payload(
            dependency_graph=[DependencyEdge(from_file="a", to_file="b", imported_symbols=[])] * 4
        )
        # One architecture finding (counts toward ACS) + one security
        # finding (must NOT count toward ACS, since it isn't a claim about
        # dependency-graph edges).
        findings = [
            Finding(agent="agent_2a_struct", file_path="a", description="bad edge", severity="medium"),
            Finding(agent="agent_2c_security", file_path="package.json", description="cve", severity="high"),
        ]
        state = _state(findings, ast_payload)
        with patch("app.graph.nodes.agent_3_critic.get_llm_client", return_value=MagicMock(complete=AsyncMock(return_value="narrative"))):
            result = await agent_3_critic(state)
        # 4 deps, 1 architecture violation -> (4-1)/4*100 = 75, not (4-2)/4*100 = 50
        assert result["acs_score"] == 75.0

    @pytest.mark.asyncio
    async def test_hallucination_triggers_retry_and_resets_findings(self, monkeypatch):
        self._patch_common(monkeypatch)
        ast_payload = _ast_payload(symbols=[])  # nothing matches -> hallucination
        findings = [
            Finding(agent="agent_2a_struct", file_path="a", description="fake", severity="low", symbol_ref="ghost"),
        ]
        state = _state(findings, ast_payload, hallucination_retry_count=0)
        with patch("app.graph.nodes.agent_3_critic.get_llm_client", return_value=MagicMock(complete=AsyncMock(return_value="narrative"))):
            result = await agent_3_critic(state)
        assert result["critic_wants_retry"] is True
        assert result["hallucination_retry_count"] == 1
        # ResetFindings sentinel, not a plain empty list that would just
        # append zero items via the additive reducer.
        from app.graph.state import ResetFindings
        assert isinstance(result["findings"], ResetFindings)

    @pytest.mark.asyncio
    async def test_retry_capped_by_settings(self, monkeypatch):
        self._patch_common(monkeypatch)
        ast_payload = _ast_payload(symbols=[])
        findings = [
            Finding(agent="agent_2a_struct", file_path="a", description="fake", severity="low", symbol_ref="ghost"),
        ]
        # Already at the cap (default 3) -> must not ask for another retry.
        state = _state(findings, ast_payload, hallucination_retry_count=3)
        with patch("app.graph.nodes.agent_3_critic.get_llm_client", return_value=MagicMock(complete=AsyncMock(return_value="narrative"))):
            result = await agent_3_critic(state)
        assert result["critic_wants_retry"] is False
        assert "findings" not in result

    @pytest.mark.asyncio
    async def test_regression_always_escalates_to_critical(self, monkeypatch):
        self._patch_common(monkeypatch, baseline_acs=99.0)
        ast_payload = _ast_payload(
            dependency_graph=[DependencyEdge(from_file="a", to_file="b", imported_symbols=[])]
        )
        findings = [Finding(agent="agent_2a_struct", file_path="a", description="bad", severity="low")]
        state = _state(findings, ast_payload)
        with patch("app.graph.nodes.agent_3_critic.get_llm_client", return_value=MagicMock(complete=AsyncMock(return_value="narrative"))):
            result = await agent_3_critic(state)
        assert result["is_regression"] is True
        assert result["hitl_severity"] == "critical"
