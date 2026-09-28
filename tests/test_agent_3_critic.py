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
        verified, hallucinated = _verify_findings(_state([finding], ast_payload))
        assert verified == [finding]
        assert hallucinated == []

    def test_symbol_ref_naming_nonexistent_symbol_is_dropped(self):
        ast_payload = _ast_payload(symbols=[])
        finding = Finding(
            agent="agent_2a_struct", file_path="a.ts", description="madeUpFn is unsafe",
            severity="high", symbol_ref="madeUpFn",
        )
        verified, hallucinated = _verify_findings(_state([finding], ast_payload))
        assert verified == []
        assert hallucinated == [finding]

    def test_dependency_edge_ref_matching_real_edge_is_kept(self):
        ast_payload = _ast_payload(
            dependency_graph=[DependencyEdge(from_file="api.ts", to_file="db.ts", imported_symbols=["Client"])]
        )
        finding = Finding(
            agent="agent_2a_struct", file_path="api.ts", description="layer crossing",
            severity="medium", dependency_edge_ref=("api.ts", "db.ts"),
        )
        verified, hallucinated = _verify_findings(_state([finding], ast_payload))
        assert verified == [finding]
        assert hallucinated == []

    def test_dependency_edge_ref_naming_nonexistent_edge_is_dropped(self):
        ast_payload = _ast_payload(dependency_graph=[])
        finding = Finding(
            agent="agent_2a_struct", file_path="api.ts", description="layer crossing",
            severity="medium", dependency_edge_ref=("api.ts", "db.ts"),
        )
        verified, hallucinated = _verify_findings(_state([finding], ast_payload))
        assert verified == []
        assert hallucinated == [finding]

    def test_finding_with_no_ref_passes_through_unverified(self):
        # Security/supply-chain findings (Agent 2C) have no AST claim to
        # check — they must not be silently dropped just because they
        # carry neither symbol_ref nor dependency_edge_ref.
        ast_payload = _ast_payload()
        finding = Finding(
            agent="agent_2c_security", file_path="package.json",
            description="Known vulnerability in left-pad@1.0.0", severity="high",
        )
        verified, hallucinated = _verify_findings(_state([finding], ast_payload))
        assert verified == [finding]
        assert hallucinated == []

    def test_architecture_finding_with_no_ref_at_all_is_dropped(self):
        # The gap this closes: verification used to be opt-in from the
        # model's side — a vague architecture finding that never made a
        # checkable claim sailed through as "unverified by design" instead
        # of being held to the same bar as a specific-but-wrong one.
        ast_payload = _ast_payload()
        finding = Finding(
            agent="agent_2a_struct", file_path="a.ts", description="something seems off",
            severity="medium",
        )
        verified, hallucinated = _verify_findings(_state([finding], ast_payload))
        assert verified == []
        assert hallucinated == [finding]

    def test_non_architecture_finding_with_no_ref_still_passes_through(self):
        # Mandatory verification is scoped to Agent 2A only — Agent 2B
        # (logic/chaos) can legitimately flag a cross-cutting issue that
        # doesn't reduce to one declared symbol, and Agent 2C has no AST
        # claim to make at all.
        ast_payload = _ast_payload()
        finding = Finding(
            agent="agent_2b_chaos", file_path="a.ts", description="possible N+1 pattern",
            severity="medium",
        )
        verified, hallucinated = _verify_findings(_state([finding], ast_payload))
        assert verified == [finding]
        assert hallucinated == []

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
        verified, hallucinated = _verify_findings(_state([real, fake], ast_payload))
        assert verified == [real]
        assert hallucinated == [fake]


class TestVerificationTier:
    """
    A finding surviving hallucination verification (its symbol/edge is real)
    is a different, weaker claim than a finding proven to violate a hard
    rule — only the latter should ever be shown as fact_checked.
    """

    def test_2a_edge_matching_a_boundary_rule_is_fact_checked(self):
        ast_payload = _ast_payload(
            dependency_graph=[
                DependencyEdge(from_file="app/repositories/ledger.py", to_file="app/main.py", imported_symbols=[]),
            ]
        )
        finding = Finding(
            agent="agent_2a_struct", file_path="app/repositories/ledger.py", description="layering inversion",
            severity="high", dependency_edge_ref=("app/repositories/ledger.py", "app/main.py"),
        )
        verified, _ = _verify_findings(_state([finding], ast_payload))
        assert verified[0].verification_tier == "fact_checked"

    def test_2a_edge_with_no_boundary_rule_is_contextual(self):
        # The edge is real (verification passes), but nothing in the
        # boundary spec says this direction is a violation — proving an
        # edge exists is not the same as proving it's a problem.
        ast_payload = _ast_payload(
            dependency_graph=[
                DependencyEdge(from_file="app/graph/state.py", to_file="app/graph/scoring.py", imported_symbols=[]),
            ]
        )
        finding = Finding(
            agent="agent_2a_struct", file_path="app/graph/state.py", description="tight coupling",
            severity="low", dependency_edge_ref=("app/graph/state.py", "app/graph/scoring.py"),
        )
        verified, _ = _verify_findings(_state([finding], ast_payload))
        assert verified[0].verification_tier == "contextual"

    def test_2a_symbol_ref_finding_is_contextual_even_when_verified(self):
        ast_payload = _ast_payload(
            symbols=[SymbolRef(file_path="a.ts", symbol_name="doThing", kind="function", line=5)]
        )
        finding = Finding(
            agent="agent_2a_struct", file_path="a.ts", description="doThing is unsafe",
            severity="high", symbol_ref="doThing",
        )
        verified, _ = _verify_findings(_state([finding], ast_payload))
        assert verified[0].verification_tier == "contextual"

    def test_2b_and_2c_findings_are_never_fact_checked(self):
        ast_payload = _ast_payload()
        findings = [
            Finding(agent="agent_2b_chaos", file_path="a.ts", description="N+1 pattern", severity="medium"),
            Finding(agent="agent_2c_security", file_path="package.json", description="cve", severity="high"),
        ]
        verified, _ = _verify_findings(_state(findings, ast_payload))
        assert all(f.verification_tier == "contextual" for f in verified)


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
        # dependency-graph edges). The architecture finding needs a real,
        # verifiable dependency_edge_ref now that verification is
        # mandatory for agent_2a_struct.
        findings = [
            Finding(
                agent="agent_2a_struct", file_path="a", description="bad edge", severity="medium",
                dependency_edge_ref=("a", "b"),
            ),
            Finding(agent="agent_2c_security", file_path="package.json", description="cve", severity="high"),
        ]
        state = _state(findings, ast_payload)
        with patch("app.graph.nodes.agent_3_critic.get_llm_client", return_value=MagicMock(complete=AsyncMock(return_value="narrative"))):
            result = await agent_3_critic(state)
        # 4 deps, 1 architecture violation -> (4-1)/4*100 = 75, not (4-2)/4*100 = 50
        assert result["acs_score"] == 75.0

    @pytest.mark.asyncio
    async def test_hallucination_triggers_retry_and_clears_only_agent_2a_findings(self, monkeypatch):
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
        # ClearAgentFindings sentinel scoped to agent_2a_struct, not a
        # plain empty list (which would just append zero items via the
        # additive reducer) and not a full wipe of every agent's findings.
        from app.graph.state import ClearAgentFindings
        assert isinstance(result["findings"], ClearAgentFindings)
        assert result["findings"].agent == "agent_2a_struct"

    @pytest.mark.asyncio
    async def test_hallucination_triggers_retry_and_records_rejected_claims(self, monkeypatch):
        self._patch_common(monkeypatch)
        ast_payload = _ast_payload(symbols=[])
        findings = [
            Finding(agent="agent_2a_struct", file_path="a", description="fake", severity="low", symbol_ref="ghost"),
        ]
        state = _state(findings, ast_payload, hallucination_retry_count=0)
        with patch("app.graph.nodes.agent_3_critic.get_llm_client", return_value=MagicMock(complete=AsyncMock(return_value="narrative"))):
            result = await agent_3_critic(state)
        assert len(result["rejected_claims"]) == 1
        assert result["rejected_claims"][0].symbol_ref == "ghost"
        assert result["rejected_claims"][0].description == "fake"

    @pytest.mark.asyncio
    async def test_retry_preserves_agent_2b_and_2c_findings_from_the_same_pass(self, monkeypatch):
        # Only agent_2a_struct is re-run on retry (see workflow.py's narrow
        # retry edge) — 2B/2C's already-verified findings from this same
        # pass must not be discarded just because 2A hallucinated.
        self._patch_common(monkeypatch)
        ast_payload = _ast_payload(symbols=[])
        findings = [
            Finding(agent="agent_2a_struct", file_path="a", description="fake", severity="low", symbol_ref="ghost"),
            Finding(agent="agent_2b_chaos", file_path="b", description="real N+1", severity="medium"),
            Finding(agent="agent_2c_security", file_path="package.json", description="cve", severity="high"),
        ]
        state = _state(findings, ast_payload, hallucination_retry_count=0)
        with patch("app.graph.nodes.agent_3_critic.get_llm_client", return_value=MagicMock(complete=AsyncMock(return_value="narrative"))):
            result = await agent_3_critic(state)
        from app.graph.state import merge_findings
        merged = merge_findings(state.findings, result["findings"])
        assert [f.agent for f in merged] == ["agent_2b_chaos", "agent_2c_security"]

    @pytest.mark.asyncio
    async def test_hallucination_from_non_2a_agent_does_not_trigger_retry(self, monkeypatch):
        # The retry edge only re-invokes agent_2a_struct, so a hallucinated
        # ref from an agent that isn't 2A can't be fixed by retrying —
        # retrying would be pure waste, not just ineffective.
        self._patch_common(monkeypatch)
        ast_payload = _ast_payload(symbols=[])
        findings = [
            Finding(agent="agent_2b_chaos", file_path="a", description="fake", severity="low", symbol_ref="ghost"),
        ]
        state = _state(findings, ast_payload, hallucination_retry_count=0)
        with patch("app.graph.nodes.agent_3_critic.get_llm_client", return_value=MagicMock(complete=AsyncMock(return_value="narrative"))):
            result = await agent_3_critic(state)
        assert result["critic_wants_retry"] is False
        assert "findings" not in result
        assert result["verified_findings"] == []

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
        findings = [
            Finding(
                agent="agent_2a_struct", file_path="a", description="bad", severity="low",
                dependency_edge_ref=("a", "b"),
            )
        ]
        state = _state(findings, ast_payload)
        with patch("app.graph.nodes.agent_3_critic.get_llm_client", return_value=MagicMock(complete=AsyncMock(return_value="narrative"))):
            result = await agent_3_critic(state)
        assert result["is_regression"] is True
        assert result["hitl_severity"] == "critical"

    @pytest.mark.asyncio
    async def test_incident_store_never_tags_a_contextual_finding_as_verified(self, monkeypatch):
        record_incident = AsyncMock()
        monkeypatch.setattr(
            "app.graph.nodes.agent_3_critic.LedgerRepository",
            lambda: MagicMock(get_baseline=lambda repo: None),
        )
        monkeypatch.setattr(
            "app.graph.nodes.agent_3_critic.VectorStore",
            lambda: MagicMock(record_incident=record_incident),
        )
        monkeypatch.setattr("pathlib.Path.read_text", lambda self: "{verified_findings}")

        ast_payload = _ast_payload(
            dependency_graph=[
                DependencyEdge(from_file="app/repositories/ledger.py", to_file="app/main.py", imported_symbols=[]),
            ]
        )
        findings = [
            # fact_checked: a real edge that matches a boundary-spec rule.
            Finding(
                agent="agent_2a_struct", file_path="app/repositories/ledger.py", description="layering inversion",
                severity="high", dependency_edge_ref=("app/repositories/ledger.py", "app/main.py"),
            ),
            # contextual: a security finding with no AST claim at all.
            Finding(agent="agent_2c_security", file_path="package.json", description="cve", severity="high"),
        ]
        state = _state(findings, ast_payload)
        with patch("app.graph.nodes.agent_3_critic.get_llm_client", return_value=MagicMock(complete=AsyncMock(return_value="narrative"))):
            await agent_3_critic(state)

        recorded_metadata = [call.kwargs["metadata"] for call in record_incident.await_args_list]
        assert len(recorded_metadata) == 2
        for metadata in recorded_metadata:
            if metadata["verification_tier"] == "contextual":
                assert metadata["source"] != "verified"
                assert metadata["source"] == "unverified_llm"
            else:
                assert metadata["verification_tier"] == "fact_checked"
                assert metadata["source"] == "verified"

    @pytest.mark.asyncio
    async def test_regression_tolerance_absorbs_a_trivial_drop(self, monkeypatch):
        # A tiny drop against the baseline (0.5 points, under the default
        # 1.0 tolerance) shouldn't page a human — that's exactly the noise
        # regression_tolerance exists to absorb.
        self._patch_common(monkeypatch, baseline_acs=100.0)
        ast_payload = _ast_payload(
            dependency_graph=[DependencyEdge(from_file="a", to_file="b", imported_symbols=[])] * 200
        )
        findings = [
            Finding(
                agent="agent_2a_struct", file_path="a", description="minor", severity="low",
                dependency_edge_ref=("a", "b"),
            )
        ]
        state = _state(findings, ast_payload)  # (200-1)/200*100 = 99.5, a 0.5-point drop
        with patch("app.graph.nodes.agent_3_critic.get_llm_client", return_value=MagicMock(complete=AsyncMock(return_value="narrative"))):
            result = await agent_3_critic(state)
        assert result["acs_score"] == 99.5
        assert result["is_regression"] is False
