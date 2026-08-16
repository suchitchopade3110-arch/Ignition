"""
Integration test: webhook receipt -> review execution -> GitHub comment
post, end to end at the orchestration level — does this actually work,
not just do the individual functions return the right values in isolation.

MOCKING APPROACH (read this before assuming a pattern/library):
  - Plain stdlib `unittest.mock` (patch / AsyncMock / MagicMock) — no new
    dependency (no responses, no httpx-mock, no pytest-mock). Nothing else
    in tests/ uses a mocking library today, so there was no existing
    convention to match; stdlib is the minimal-footprint choice and is
    already available via Python itself.
  - GitHub, Groq (LLM), and Supabase are the three externals this task
    requires mocking, per the prompt. Two more real network calls this
    test would otherwise make are mocked too, for the same reason (CI
    must be deterministic/fast/free, not because the prompt named them):
    the Bun AST analyzer service (ASTClient.analyze_git) and the
    sentence-transformers embedding model / RAG vector store
    (VectorStore.similar_incidents/record_incident) — loading a real
    embedding model on every CI run would be slow and pointless for what
    this test is actually checking.
  - Supabase: NOT mocked by faking Supabase's own fluent query client
    (`.table().select().eq()...`) — that would mean reimplementing
    Supabase's query semantics in a fake, which is more machinery than
    this needs. Instead, `review_repo`/`repo_repo` (the actual singleton
    instances imported by both app.main and app.services.review_pipeline
    — same objects, so patching their methods affects both modules at
    once) have their persistence METHODS replaced with a small in-memory
    dict-backed fake (FakeReviewRepo/FakeRepoRepo below). This exercises
    the real webhook handler, real signature verification, real graph
    traversal/routing, real GitHub-post orchestration — only the actual
    database round-trip is faked.
  - Redis/Arq: also mocked (get_arq_pool AND stream_manager.publish — both
    Redis touchpoints, not just the job queue one), not run against a real
    Redis instance. This keeps the whole suite runnable with zero external
    services (no service container needed in CI), at the cost of not
    testing Arq's own enqueue/dequeue mechanics — those are Arq's
    responsibility to have already tested, not this project's job function
    logic. After confirming the webhook enqueues (mocked), the test
    directly awaits run_review_job() to simulate what the real worker
    would execute — genuinely running the real graph, real routing, real
    GitHub-post call, not a stand-in for any of that.
    (First draft of this test only mocked get_arq_pool and missed
    stream_manager.publish's own separate Redis client — passed locally
    only because a real Redis happened to be running on this dev machine,
    which meant the suite wasn't actually hermetic. CI, correctly having
    no Redis at all, caught this immediately.)
  - Patches target the CLASS/METHOD (e.g. `LLMClient.complete`,
    `GitHubClient` itself, `VectorStore.similar_incidents`) rather than
    per-module import bindings, specifically because several call sites
    import these names independently across multiple graph node files —
    patching the class means every caller picks it up regardless of which
    module holds a reference, sidestepping a "patch where it's used, not
    where it's defined" mismatch across four different node files.
"""
import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

import app.main as main_module
from app.services.review_pipeline import review_repo, repo_repo, run_review_job
from app.services.ast_client import ASTClient
from app.services.llm_client import LLMClient
from app.services.github_client import GitHubClient
from app.services.stream_manager import stream_manager
from app.rag.vector_store import VectorStore
from app.repositories.ledger import LedgerRepository
from app.schemas.ast_payload import ASTAnalyzerPayload
from app.config import get_settings


class FakeReviewRepo:
    """In-memory stand-in for ReviewRepository — same method names/shapes
    the real code calls, backed by a dict instead of Supabase."""

    def __init__(self):
        self.rows: dict[str, dict] = {}

    def create_review(self, review_id, repo_full_name, pr_number, title, author, branch,
                       commit_sha, installation_id=None, correlation_id=None):
        # Mirrors the real repo's unique constraint on
        # (repo_full_name, pr_number, commit_sha) — see
        # migrations_004_webhook_dedupe.sql — so the dedupe test exercises
        # the real github_webhook code path (its except APIError branch),
        # not a special-cased test double.
        for row in self.rows.values():
            if (row["repo_full_name"], row["pr_number"], row["commit_sha"]) == (
                repo_full_name, pr_number, commit_sha,
            ):
                from postgrest.exceptions import APIError
                raise APIError({"code": "23505", "message": "duplicate key value violates unique constraint"})
        row = {
            "id": review_id, "repo_full_name": repo_full_name, "pr_number": pr_number,
            "title": title, "author": author, "branch": branch, "commit_sha": commit_sha,
            "installation_id": installation_id, "correlation_id": correlation_id,
            "status": "queued",
        }
        self.rows[review_id] = row
        return row

    def update_review(self, review_id, updates: dict):
        self.rows.setdefault(review_id, {})
        self.rows[review_id].update(updates)
        return self.rows[review_id]

    def get_review(self, review_id):
        return self.rows.get(review_id)

    def get_review_by_repo_pr_sha(self, repo_full_name, pr_number, commit_sha):
        for row in self.rows.values():
            if (row.get("repo_full_name"), row.get("pr_number"), row.get("commit_sha")) == (
                repo_full_name, pr_number, commit_sha,
            ):
                return {"id": row["id"], "correlation_id": row.get("correlation_id")}
        return None

    def get_review_github_context(self, review_id):
        row = self.rows.get(review_id)
        if not row:
            return None
        return {
            "repo_full_name": row.get("repo_full_name"),
            "installation_id": row.get("installation_id"),
            "pr_number": row.get("pr_number"),
            "final_comment_markdown": row.get("final_comment_markdown"),
            "correlation_id": row.get("correlation_id"),
        }


class FakeRepoRepo:
    def __init__(self):
        self.repos: dict[str, dict] = {}
        self.stats_calls: list[dict] = []

    def get_or_create_repo(self, repo_full_name):
        repo_id = repo_full_name.replace("/", "_")
        self.repos.setdefault(repo_id, {"id": repo_id})
        return self.repos[repo_id]

    def update_repo_stats(self, repo_full_name, acs_score, last_review_at):
        self.stats_calls.append({"repo_full_name": repo_full_name, "acs_score": acs_score})


def _sign(body: bytes) -> str:
    secret = get_settings().github_webhook_secret
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _webhook_payload() -> dict:
    return {
        "action": "opened",
        "repository": {
            "full_name": "acme/widgets",
            "default_branch": "main",
            "clone_url": "https://github.com/acme/widgets.git",
        },
        "pull_request": {
            "number": 7,
            "diff_url": "https://github.com/acme/widgets/pull/7.diff",
            "head": {"sha": "deadbeef00000000000000000000000000000000"},
            "base": {"sha": "0000000000000000000000000000000000000000"},
        },
        "installation": {"id": 999},
    }


def _fake_ast_payload() -> ASTAnalyzerPayload:
    return ASTAnalyzerPayload(
        repo_full_name="acme/widgets",
        pr_number=7,
        changed_files=["src/index.ts"],
        symbols=[],
        dependency_graph=[],
        hard_rule_violations=[],
        changed_packages=[],  # empty on purpose: skips agent_2c's OSV/LLM calls too
    )


async def _fake_llm_complete(self, prompt, json_mode=True, agent_name="unknown"):
    """No findings, clean pass — the simplest deterministic path through
    the graph to finalize_and_post -> GitHubClient.post_review_comment,
    which is the actual thing this test verifies gets called."""
    if not json_mode:
        return "Clean pass, no notable issues."
    return json.dumps({"findings": []})


@pytest.fixture
def fake_repos(monkeypatch):
    fake_review_repo = FakeReviewRepo()
    fake_repo_repo = FakeRepoRepo()
    # review_repo/repo_repo are the actual singleton instances imported by
    # both app.main and app.services.review_pipeline (same objects) —
    # patching their bound methods here affects both call paths at once.
    for name in ("create_review", "update_review", "get_review",
                 "get_review_by_repo_pr_sha", "get_review_github_context"):
        monkeypatch.setattr(review_repo, name, getattr(fake_review_repo, name))
    for name in ("get_or_create_repo", "update_repo_stats"):
        monkeypatch.setattr(repo_repo, name, getattr(fake_repo_repo, name))
    # The one call site that touches review_repo._db directly (the
    # previous-ACS-score lookup) rather than going through a named method.
    fake_db = MagicMock()
    fake_db.table.return_value.select.return_value.eq.return_value.eq.return_value \
        .order.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
    monkeypatch.setattr(review_repo, "_db", fake_db)
    return fake_review_repo, fake_repo_repo


@pytest.fixture
def mock_externals():
    with patch.object(ASTClient, "analyze_git", new=AsyncMock(return_value=_fake_ast_payload())), \
         patch.object(LLMClient, "complete", new=_fake_llm_complete), \
         patch.object(VectorStore, "similar_incidents", new=AsyncMock(return_value=[])), \
         patch.object(VectorStore, "record_incident", new=AsyncMock(return_value=None)), \
         patch.object(LedgerRepository, "get_baseline", return_value=None), \
         patch("app.services.github_client.GitHubClient") as mock_gh_class:
        mock_gh_instance = MagicMock()
        mock_gh_instance.post_review_comment.return_value = {
            "id": 555111, "html_url": "https://github.com/acme/widgets/pull/7#issuecomment-555111",
        }
        # get_pr_diff and the raw PyGithub PR object both need to return
        # real strings, not an unconfigured MagicMock — ReviewState.diff_text
        # is a real pydantic string field, and pydantic correctly rejects a
        # MagicMock there. This is exactly the kind of gap real validation
        # catches; left unconfigured on the first pass and pydantic caught it.
        mock_gh_instance.get_pr_diff.return_value = (
            "diff --git a/src/index.ts b/src/index.ts\n+// no-op change\n"
        )
        fake_pr = MagicMock()
        fake_pr.title = "Test PR"
        fake_pr.user.login = "test-author"
        fake_pr.head.ref = "test-branch"
        mock_gh_instance._client.get_repo.return_value.get_pull.return_value = fake_pr
        mock_gh_class.return_value = mock_gh_instance
        yield {"github_client": mock_gh_class, "github_instance": mock_gh_instance}


@pytest.fixture
def mock_arq(monkeypatch):
    fake_job = MagicMock()
    fake_job.job_id = "fake-job-id-123"
    fake_pool = AsyncMock()
    fake_pool.enqueue_job = AsyncMock(return_value=fake_job)

    async def fake_get_arq_pool():
        return fake_pool

    monkeypatch.setattr(main_module, "get_arq_pool", fake_get_arq_pool)
    # stream_manager.publish is the OTHER real-Redis touchpoint (SSE
    # pub/sub) that run_review_job hits repeatedly — separate from the
    # job-queue Redis client above, and easy to miss for exactly that
    # reason (see the module docstring's note on this).
    monkeypatch.setattr(stream_manager, "publish", AsyncMock(return_value=None))
    return fake_pool


@pytest.mark.asyncio
async def test_webhook_to_review_to_github_comment(fake_repos, mock_externals, mock_arq):
    fake_review_repo, fake_repo_repo = fake_repos
    body = json.dumps(_webhook_payload()).encode()
    signature = _sign(body)

    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/webhooks/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": signature,
                "X-GitHub-Delivery": "test-delivery-1",
            },
        )

    # 1. Webhook receipt: real signature verification, real payload
    # parsing, real repo/review persistence orchestration (fake DB).
    assert response.status_code == 202
    body_json = response.json()
    review_id = body_json["reviewId"]
    assert body_json["status"] == "queued"
    assert review_id in fake_review_repo.rows
    assert fake_review_repo.rows[review_id]["repo_full_name"] == "acme/widgets"

    # Arq enqueue was attempted with the right job args (mocked, not real
    # Redis — see module docstring for why).
    mock_arq.enqueue_job.assert_awaited_once()
    enqueue_args = mock_arq.enqueue_job.call_args.args
    assert enqueue_args[0] == "run_review_job"
    assert enqueue_args[2] == review_id  # review_id positional arg

    # 2. Review execution: run the real job function directly (this is
    # what the real Arq worker would execute) — real graph traversal, real
    # routing decisions, only the LLM/GitHub/AST/Supabase boundaries mocked.
    event_payload, _, correlation_id = enqueue_args[1], enqueue_args[2], enqueue_args[3]
    await run_review_job({}, event_payload, review_id, correlation_id)

    # 3. GitHub comment: the actual thing this whole flow exists to
    # produce. Assert it was called with the right repo/PR, not just that
    # *something* was called.
    mock_externals["github_instance"].post_review_comment.assert_called_once()
    call_kwargs = mock_externals["github_instance"].post_review_comment.call_args.kwargs
    assert call_kwargs["repo_full_name"] == "acme/widgets"
    assert call_kwargs["pr_number"] == 7

    # Final review state reflects a completed, clean pass.
    final = fake_review_repo.get_review(review_id)
    assert final["status"] == "completed"


@pytest.mark.asyncio
async def test_duplicate_webhook_delivery_does_not_start_second_run(fake_repos, mock_externals, mock_arq):
    """The dedupe check (repo, pr_number, commit_sha) — a second identical
    delivery must not enqueue a second job."""
    fake_review_repo, _ = fake_repos
    payload = _webhook_payload()
    body = json.dumps(payload).encode()
    signature = _sign(body)

    # FakeReviewRepo.create_review enforces the (repo, pr_number,
    # commit_sha) uniqueness constraint itself (mirrors the real DB), so
    # the second identical delivery naturally hits github_webhook's real
    # except APIError branch — nothing test-specific needed here.
    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post(
            "/webhooks/github", content=body,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": signature,
                     "X-GitHub-Delivery": "dup-test-1"},
        )
        second = await client.post(
            "/webhooks/github", content=body,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": signature,
                     "X-GitHub-Delivery": "dup-test-2"},
        )

    assert first.status_code == 202
    assert first.json()["status"] == "queued"
    assert second.status_code == 202
    assert second.json()["status"] == "duplicate"
    assert second.json()["reviewId"] == first.json()["reviewId"]
    # Only one enqueue_job call total, not two.
    assert mock_arq.enqueue_job.await_count == 1
