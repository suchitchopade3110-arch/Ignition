"""
Audit P1-11: Agent 2C fanned out one LLM call (plus OSV and npm calls) per
changed package, with no limit. Now:
  - prefilter: only a package that is NEW in this PR (not a version bump)
    and either published < 7 days ago or within edit distance 2 of a
    popular npm name goes to the model; with no popular list, every new
    package does (fail toward checking, never toward skipping);
  - batch: one prompt for all of them, one findings array back;
  - bound: OSV and npm calls share an asyncio.Semaphore(4).
A 50-package lockfile bump then makes at most one LLM call.
"""
import asyncio
import json

import pytest

from app.graph.nodes import agent_2c_security as a2c
from app.graph.state import ReviewState
from app.schemas.ast_payload import ASTAnalyzerPayload, PackageRef

POPULAR = frozenset({"lodash", "react", "express", "left-pad", "@babel/core"})


def _state(packages):
    payload = ASTAnalyzerPayload(repo_full_name="acme/widgets", pr_number=1, changed_files=["package.json"],
                                 symbols=[], dependency_graph=[], changed_packages=packages)
    return ReviewState(repo_full_name="acme/widgets", pr_number=1, installation_id=1, ast_payload=payload)


class Harness:
    """Fake OSV/npm lookups that track how many run at once, and an LLM that
    records each prompt."""

    def __init__(self, monkeypatch, publish_age=900.0, popular=POPULAR, llm_reply=None):
        self.in_flight = 0
        self.max_in_flight = 0
        self.prompts: list[str] = []
        harness = self

        async def tracked(result):
            harness.in_flight += 1
            harness.max_in_flight = max(harness.max_in_flight, harness.in_flight)
            await asyncio.sleep(0.01)
            harness.in_flight -= 1
            return result

        async def osv(client, name, version):
            return await tracked([])

        async def npm_age(client, name, version):
            return await tracked(publish_age(name) if callable(publish_age) else publish_age)

        class LLM:
            async def complete(self, prompt, json_mode=True, agent_name="unknown"):
                harness.prompts.append(prompt)
                return llm_reply or json.dumps({"findings": []})

        monkeypatch.setattr(a2c, "_phase1_deterministic_registry_check", osv)
        monkeypatch.setattr(a2c, "_fetch_publish_age_days", npm_age)
        monkeypatch.setattr(a2c, "get_llm_client", lambda: LLM())
        monkeypatch.setattr(a2c, "load_popular_packages", lambda: popular, raising=False)


@pytest.mark.asyncio
async def test_a_50_package_version_bump_makes_no_llm_call(monkeypatch):
    h = Harness(monkeypatch, publish_age=1.0)  # all freshly published, but all just bumps
    bumps = [PackageRef(name=f"pkg-{i}", version="2.0.0", previous_version="1.0.0") for i in range(50)]
    out = await a2c.agent_2c_security(_state(bumps))
    assert h.prompts == []
    # The deterministic freshness finding still covers every bumped package.
    assert sum("published to npm" in f.description for f in out["findings"]) == 50
    assert "agent_errors" not in out


@pytest.mark.asyncio
async def test_50_new_suspicious_packages_make_exactly_one_batched_call(monkeypatch):
    h = Harness(monkeypatch, publish_age=1.0)
    new = [PackageRef(name=f"fresh-{i}", version="1.0.0") for i in range(50)]
    await a2c.agent_2c_security(_state(new))
    assert len(h.prompts) == 1
    assert all(f"fresh-{i}" in h.prompts[0] for i in range(50))


@pytest.mark.asyncio
async def test_osv_and_npm_calls_never_exceed_four_at_once(monkeypatch):
    h = Harness(monkeypatch)
    await a2c.agent_2c_security(_state([PackageRef(name=f"p{i}", version="1.0.0") for i in range(30)]))
    assert 1 < h.max_in_flight <= 4


@pytest.mark.parametrize("pkg, age, expected", [
    (PackageRef(name="lodahs", version="1.0.0"), 900.0, True),            # 2 edits from "lodash"
    (PackageRef(name="reactt", version="1.0.0"), 900.0, True),            # 1 edit from "react"
    (PackageRef(name="@babel/c0re", version="1.0.0"), 900.0, True),       # scoped names too
    (PackageRef(name="lodash", version="4.17.21"), 900.0, False),         # IS the popular package
    (PackageRef(name="totally-unrelated", version="1.0.0"), 900.0, False),
    (PackageRef(name="totally-unrelated", version="1.0.0"), 2.0, True),   # published < 7 days ago
    (PackageRef(name="totally-unrelated", version="1.0.0"), None, False), # unknown age is not "fresh"
    (PackageRef(name="lodahs", version="2.0.0", previous_version="1.0.0"), 2.0, False),  # a bump
])
def test_prefilter(pkg, age, expected):
    assert a2c.needs_llm_review(pkg, age, POPULAR, fresh_days=7) is expected


def test_without_a_popular_list_every_new_package_is_checked():
    old_unrelated = PackageRef(name="totally-unrelated", version="1.0.0")
    assert a2c.needs_llm_review(old_unrelated, 900.0, None, fresh_days=7) is True
    bump = PackageRef(name="totally-unrelated", version="2.0.0", previous_version="1.0.0")
    assert a2c.needs_llm_review(bump, 900.0, None, fresh_days=7) is False


@pytest.mark.asyncio
async def test_missing_popular_list_sends_every_new_package_in_one_call(monkeypatch):
    h = Harness(monkeypatch, popular=None)
    await a2c.agent_2c_security(_state([PackageRef(name=f"old-{i}", version="1.0.0") for i in range(20)]))
    assert len(h.prompts) == 1 and all(f"old-{i}" in h.prompts[0] for i in range(20))


def test_the_shipped_popular_list_loads_or_is_absent(tmp_path, monkeypatch):
    # A real file is parsed into names (comments and blanks skipped); no
    # file at all is None, which callers treat as "check every new package".
    data = tmp_path / "popular.txt"
    data.write_text("# header\nreact\n\nlodash\n")
    monkeypatch.setattr(a2c, "POPULAR_PACKAGES_PATH", data)
    a2c.load_popular_packages.cache_clear()
    try:
        assert a2c.load_popular_packages() == frozenset({"react", "lodash"})
        monkeypatch.setattr(a2c, "POPULAR_PACKAGES_PATH", tmp_path / "missing.txt")
        a2c.load_popular_packages.cache_clear()
        assert a2c.load_popular_packages() is None
    finally:
        a2c.load_popular_packages.cache_clear()
