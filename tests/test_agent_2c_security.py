"""
Agent 2C's headline claim is catching a freshly-published (e.g. "4 hours
old") package. That requires an actual registry lookup — these tests
pin down that the deterministic publish-age check uses real fetched data
(never invents an age) and that a missing/failed lookup is treated as
"unknown", never silently as "just published".
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.graph.nodes.agent_2c_security as agent_2c_security_module
from app.graph.nodes.agent_2c_security import _fetch_publish_age_days, agent_2c_security
from app.graph.state import ReviewState
from app.schemas.ast_payload import ASTAnalyzerPayload, PackageRef


@pytest.fixture(autouse=True)
def _clear_publish_age_cache():
    # _publish_age_cache is process-global by design (see its docstring),
    # which means it's also shared across test functions — several tests
    # here reuse the same package@version, so without this they'd read
    # back a previous test's cached result instead of exercising a fresh
    # lookup.
    agent_2c_security_module._publish_age_cache.clear()
    yield
    agent_2c_security_module._publish_age_cache.clear()


def _state(changed_packages: list[PackageRef]) -> ReviewState:
    return ReviewState(
        repo_full_name="acme/widgets", pr_number=1, installation_id=1,
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets", pr_number=1, changed_files=[],
            symbols=[], dependency_graph=[], changed_packages=changed_packages,
        ),
    )


class TestFetchPublishAgeDays:
    @pytest.mark.asyncio
    async def test_computes_real_age_from_registry_time_field(self):
        published_at = (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat().replace("+00:00", "Z")
        client = MagicMock()
        client.get = AsyncMock(return_value=MagicMock(
            status_code=200, json=lambda: {"time": {"1.0.0": published_at}}
        ))
        age = await _fetch_publish_age_days(client, "some-pkg", "1.0.0")
        assert age is not None
        assert 0 <= age < 1  # ~4 hours old

    @pytest.mark.asyncio
    async def test_returns_none_not_zero_when_version_missing_from_registry(self):
        client = MagicMock()
        client.get = AsyncMock(return_value=MagicMock(status_code=200, json=lambda: {"time": {}}))
        age = await _fetch_publish_age_days(client, "some-pkg", "1.0.0")
        assert age is None

    @pytest.mark.asyncio
    async def test_returns_none_on_registry_error(self):
        client = MagicMock()
        client.get = AsyncMock(return_value=MagicMock(status_code=404, json=lambda: {}))
        age = await _fetch_publish_age_days(client, "some-pkg", "1.0.0")
        assert age is None

    @pytest.mark.asyncio
    async def test_returns_none_on_network_exception(self):
        client = MagicMock()
        client.get = AsyncMock(side_effect=RuntimeError("boom"))
        age = await _fetch_publish_age_days(client, "some-pkg", "1.0.0")
        assert age is None

    @pytest.mark.asyncio
    async def test_successful_lookup_is_cached_across_calls(self, monkeypatch):
        # A publish date never changes, so a second lookup for the same
        # package@version must not hit the registry again.
        monkeypatch.setattr(agent_2c_security_module, "_publish_age_cache", {})
        published_at = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat().replace("+00:00", "Z")
        client = MagicMock()
        client.get = AsyncMock(return_value=MagicMock(
            status_code=200, json=lambda: {"time": {"1.0.0": published_at}}
        ))
        first = await _fetch_publish_age_days(client, "cached-pkg", "1.0.0")
        second = await _fetch_publish_age_days(client, "cached-pkg", "1.0.0")
        assert client.get.await_count == 1
        assert first == pytest.approx(second, abs=0.01)

    @pytest.mark.asyncio
    async def test_failed_lookup_is_not_cached(self, monkeypatch):
        # A transient failure must be retried next time, never permanently
        # remembered as "unknown".
        monkeypatch.setattr(agent_2c_security_module, "_publish_age_cache", {})
        client = MagicMock()
        client.get = AsyncMock(return_value=MagicMock(status_code=500, json=lambda: {}))
        await _fetch_publish_age_days(client, "flaky-pkg", "1.0.0")
        await _fetch_publish_age_days(client, "flaky-pkg", "1.0.0")
        assert client.get.await_count == 2


class TestAgentTwoCSecurity:
    @pytest.mark.asyncio
    async def test_freshly_published_package_flagged_deterministically(self, monkeypatch):
        monkeypatch.setattr(
            "app.graph.nodes.agent_2c_security._phase1_deterministic_registry_check",
            AsyncMock(return_value=[]),
        )
        monkeypatch.setattr(
            "app.graph.nodes.agent_2c_security._fetch_publish_age_days",
            AsyncMock(return_value=0.17),  # ~4 hours
        )
        monkeypatch.setattr(
            "app.graph.nodes.agent_2c_security._phase2_semantic_slopsquat_check",
            AsyncMock(return_value=[]),
        )
        state = _state([PackageRef(name="totally-legit-pkg", version="1.0.0")])
        result = await agent_2c_security(state)
        descriptions = [f.description for f in result["findings"]]
        assert any("published to npm" in d and "0.2" in d or "0.17" in d for d in descriptions)

    @pytest.mark.asyncio
    async def test_old_package_not_flagged_for_freshness(self, monkeypatch):
        monkeypatch.setattr(
            "app.graph.nodes.agent_2c_security._phase1_deterministic_registry_check",
            AsyncMock(return_value=[]),
        )
        monkeypatch.setattr(
            "app.graph.nodes.agent_2c_security._fetch_publish_age_days",
            AsyncMock(return_value=900.0),
        )
        monkeypatch.setattr(
            "app.graph.nodes.agent_2c_security._phase2_semantic_slopsquat_check",
            AsyncMock(return_value=[]),
        )
        state = _state([PackageRef(name="well-established-pkg", version="4.2.0")])
        result = await agent_2c_security(state)
        assert result["findings"] == []

    @pytest.mark.asyncio
    async def test_unknown_publish_age_never_flagged_as_fresh(self, monkeypatch):
        # A failed/missing registry lookup must not be treated as "just
        # published" — that would be a hallucinated claim about data that
        # was never actually fetched.
        monkeypatch.setattr(
            "app.graph.nodes.agent_2c_security._phase1_deterministic_registry_check",
            AsyncMock(return_value=[]),
        )
        monkeypatch.setattr(
            "app.graph.nodes.agent_2c_security._fetch_publish_age_days",
            AsyncMock(return_value=None),
        )
        monkeypatch.setattr(
            "app.graph.nodes.agent_2c_security._phase2_semantic_slopsquat_check",
            AsyncMock(return_value=[]),
        )
        state = _state([PackageRef(name="unknown-registry-pkg", version="1.0.0")])
        result = await agent_2c_security(state)
        assert result["findings"] == []

    @pytest.mark.asyncio
    async def test_duplicate_package_version_pairs_are_deduped(self, monkeypatch):
        registry_check = AsyncMock(return_value=[])
        monkeypatch.setattr(
            "app.graph.nodes.agent_2c_security._phase1_deterministic_registry_check", registry_check
        )
        monkeypatch.setattr(
            "app.graph.nodes.agent_2c_security._fetch_publish_age_days", AsyncMock(return_value=900.0)
        )
        monkeypatch.setattr(
            "app.graph.nodes.agent_2c_security._phase2_semantic_slopsquat_check", AsyncMock(return_value=[])
        )
        state = _state([
            PackageRef(name="dup-pkg", version="1.0.0"),
            PackageRef(name="dup-pkg", version="1.0.0"),
        ])
        await agent_2c_security(state)
        assert registry_check.call_count == 1
