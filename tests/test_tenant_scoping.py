"""
Audit P0-4: every signed-in user used to see every tenant's reviews, stats,
repos and HITL queue. Each list endpoint is now scoped to the repos the
user can push to (resolved from GitHub once, cached for 5 minutes), and an
empty set short-circuits without querying at all.

Uses tests/fake_supabase.py so the real repository query code runs: a
missing .in_() filter changes what these tests see.
"""
import json

import httpx
import pytest

import app.auth as auth_module
import app.main as main_module
from app.services.review_pipeline import repo_repo, review_repo
from tests.fake_supabase import FakeAsyncRedis, FakeSupabase

USERS = {
    "sess-alice": {"id": "u-alice", "github_id": 1, "login": "alice"},
    "sess-bob": {"id": "u-bob", "github_id": 2, "login": "bob"},
    "sess-carol": {"id": "u-carol", "github_id": 3, "login": "carol"},
}
# What GET /user/repos returns for each user's token. alice can also *read*
# bob's public repo — read-only access must not count.
USER_REPOS = {
    "tok-sess-alice": [
        {"full_name": "alice/app", "permissions": {"admin": True, "push": True}},
        {"full_name": "bob/svc", "permissions": {"pull": True}},
    ],
    "tok-sess-bob": [{"full_name": "bob/svc", "permissions": {"push": True}}],
    "tok-sess-carol": [],
}


def _review(rid, repo, status, acs=None, findings=0, created="2026-10-20T00:00:00+00:00"):
    return {"id": rid, "repo_full_name": repo, "pr_number": 1, "title": rid, "author": "x", "branch": "b",
            "commit_sha": rid, "status": status, "severity": "none", "acs_score": acs,
            "findings_count": findings, "created_at": created}


@pytest.fixture
def world(monkeypatch):
    db = FakeSupabase({
        "repositories": [
            {"id": "alice_app", "owner": "alice", "name": "app", "language": "TypeScript"},
            {"id": "bob_svc", "owner": "bob", "name": "svc", "language": "TypeScript"},
        ],
        "reviews": [
            _review("a-run", "alice/app", "running"),
            _review("a-hitl", "alice/app", "waiting_hitl"),
            _review("a-done", "alice/app", "completed", acs=90.0, findings=2),
            _review("b-hitl", "bob/svc", "waiting_hitl"),
            _review("b-done", "bob/svc", "completed", acs=40.0, findings=5),
        ],
    })
    for repo in (review_repo, repo_repo, auth_module._review_repo, auth_module._repo_repo):
        monkeypatch.setattr(repo, "_db", db)

    def session(session_id):
        user = USERS.get(session_id)
        return {"session_id": session_id, "github_access_token": f"tok-{session_id}", "user": user} if user else None

    monkeypatch.setattr(auth_module._auth_repo, "get_session_with_user", session)
    redis = FakeAsyncRedis()
    monkeypatch.setattr(auth_module, "get_pubsub_redis", lambda: redis, raising=False)

    github_calls: list[str] = []
    real_get = httpx.AsyncClient.get

    async def fake_get(self, url, headers=None, **kwargs):
        if not str(url).startswith("https://api.github.com"):
            return await real_get(self, url, headers=headers, **kwargs)  # the test's own app requests
        github_calls.append(url)
        token = (headers or {}).get("Authorization", "").removeprefix("Bearer ")
        request = httpx.Request("GET", url)
        if "/user/repos" in url:
            return httpx.Response(200, json=USER_REPOS[token], request=request)
        if "/repos/" in url:  # per-repo fallback in check_repo_access
            full = url.split("/repos/", 1)[1]
            perms = next((r["permissions"] for r in USER_REPOS[token] if r["full_name"] == full), None)
            if perms is None:
                return httpx.Response(404, json={}, request=request)
            return httpx.Response(200, json={"full_name": full, "permissions": perms}, request=request)
        raise AssertionError(f"unexpected GitHub call {url}")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    return {"db": db, "redis": redis, "github_calls": github_calls}


async def _get(path, session_id):
    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test",
                                 cookies={"ignition_session": session_id}) as client:
        return await client.get(path)


@pytest.mark.asyncio
@pytest.mark.parametrize("session_id, own_ids, other_ids, repo_names", [
    ("sess-alice", {"a-run", "a-hitl", "a-done"}, {"b-hitl", "b-done"}, ["app"]),
    ("sess-bob", {"b-hitl", "b-done"}, {"a-run", "a-hitl", "a-done"}, ["svc"]),
])
async def test_each_user_sees_only_their_own_rows_on_all_four_endpoints(world, session_id, own_ids, other_ids, repo_names):
    reviews = (await _get("/api/reviews", session_id)).json()
    assert {r["id"] for r in reviews["items"]} == own_ids
    assert reviews["total"] == len(own_ids)

    hitl = (await _get("/api/hitl/pending", session_id)).json()
    assert {r["id"] for r in hitl} == {i for i in own_ids if "hitl" in i}

    repos = (await _get("/api/repos", session_id)).json()
    assert sorted(r["name"] for r in repos) == repo_names

    stats = (await _get("/api/stats", session_id)).json()
    expected = {
        "sess-alice": {"activeReviews": 1, "hitlPending": 1, "avgAcsScore": 90.0, "issuesFound": 2},
        "sess-bob": {"activeReviews": 0, "hitlPending": 1, "avgAcsScore": 40.0, "issuesFound": 5},
    }[session_id]
    assert {k: stats[k] for k in expected} == expected


@pytest.mark.asyncio
async def test_user_with_no_repos_gets_empty_results_without_any_reviews_query(world):
    before = len(world["db"].queries_on("reviews")) + len(world["db"].queries_on("repositories"))
    assert (await _get("/api/reviews", "sess-carol")).json()["items"] == []
    assert (await _get("/api/hitl/pending", "sess-carol")).json() == []
    assert (await _get("/api/repos", "sess-carol")).json() == []
    stats = (await _get("/api/stats", "sess-carol")).json()
    assert (stats["activeReviews"], stats["hitlPending"], stats["issuesFound"]) == (0, 0, 0)
    after = len(world["db"].queries_on("reviews")) + len(world["db"].queries_on("repositories"))
    assert after == before


@pytest.mark.asyncio
async def test_repo_set_is_cached_for_five_minutes(world):
    await _get("/api/reviews", "sess-alice")
    await _get("/api/stats", "sess-alice")
    assert sum("/user/repos" in u for u in world["github_calls"]) == 1
    assert world["redis"].ttls["user_repos:u-alice"] == 300
    assert json.loads(world["redis"].store["user_repos:u-alice"]) == ["alice/app"]


@pytest.mark.asyncio
async def test_repo_filter_uses_the_cached_set_and_still_denies_other_tenants(world):
    own = await _get("/api/reviews?repo=alice/app", "sess-alice")
    assert own.status_code == 200
    assert not any("/repos/alice/app" in u for u in world["github_calls"])  # served from the set, no per-repo call
    other = await _get("/api/reviews?repo=bob/svc", "sess-alice")
    assert other.status_code == 403  # alice can only read bob/svc
