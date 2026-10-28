"""
Audit P0-7: regression detection never fired, because nothing ever wrote a
baseline. A merged PR now enqueues record_merge_baseline (one job per PR,
so redeliveries don't double-write); the job writes the PR's last completed
ACS to architecture_ledger; get_baseline is the median of the last 10 rows;
and the pipeline compares against that baseline, not the last review.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

import app.main as main_module
import app.repositories.ledger as ledger_module
from app.graph.nodes.agent_3_critic import agent_3_critic
from app.graph.state import Finding, ReviewState
from app.repositories.ledger import LedgerRepository
from app.schemas.ast_payload import ASTAnalyzerPayload, DependencyEdge
from app.services.review_pipeline import review_repo, run_review_job
from tests.fake_supabase import FakeSupabase
from tests.test_integration_webhook_review_comment import (  # noqa: F401  (fixtures)
    _sign, _webhook_payload, fake_repos, mock_arq, mock_externals,
)

HEAD = "deadbeef00000000000000000000000000000000"


def _closed_payload(merged: bool) -> dict:
    payload = _webhook_payload()
    payload["action"] = "closed"
    payload["pull_request"]["merged"] = merged
    return payload


async def _post(payload, delivery):
    body = json.dumps(payload).encode()
    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post("/webhooks/github", content=body, headers={
            "Content-Type": "application/json", "X-Hub-Signature-256": _sign(body), "X-GitHub-Delivery": delivery})


@pytest.mark.asyncio
async def test_merged_pr_enqueues_one_baseline_job_per_pr(fake_repos, mock_arq):
    fake_review_repo, _ = fake_repos
    res = await _post(_closed_payload(merged=True), "merge-1")
    assert res.status_code == 202 and res.json()["status"] == "baseline_queued"
    mock_arq.enqueue_job.assert_awaited_once()
    call = mock_arq.enqueue_job.await_args
    assert call.args == ("record_merge_baseline", "acme/widgets", 7, HEAD)
    assert call.kwargs["_job_id"] == "baseline:acme/widgets:7"
    assert fake_review_repo.rows == {}  # a merge is not a review


@pytest.mark.asyncio
async def test_redelivered_merge_reuses_the_same_job_id(fake_repos, mock_arq):
    await _post(_closed_payload(merged=True), "merge-1")
    await _post(_closed_payload(merged=True), "merge-1-redelivered")
    job_ids = {c.kwargs["_job_id"] for c in mock_arq.enqueue_job.await_args_list}
    assert job_ids == {"baseline:acme/widgets:7"}  # Arq refuses the second job with this id


@pytest.mark.asyncio
async def test_unmerged_close_enqueues_nothing(fake_repos, mock_arq):
    res = await _post(_closed_payload(merged=False), "close-1")
    assert res.status_code == 202 and res.json()["status"] == "ignored"
    mock_arq.enqueue_job.assert_not_awaited()


# --- the job ------------------------------------------------------------------

def _review(rid, pr, status, acs, created):
    return {"id": rid, "repo_full_name": "acme/widgets", "pr_number": pr, "status": status,
            "acs_score": acs, "created_at": created}


@pytest.fixture
def db(monkeypatch):
    db = FakeSupabase({
        "reviews": [
            _review("old", 7, "completed", 70.0, "2026-10-01T00:00:00+00:00"),
            _review("new", 7, "completed", 85.0, "2026-10-02T00:00:00+00:00"),
            _review("newest-failed", 7, "failed", None, "2026-10-03T00:00:00+00:00"),
            _review("newest-no-acs", 7, "completed", None, "2026-10-04T00:00:00+00:00"),  # 2A failed (P0-1)
            _review("other-pr", 8, "completed", 10.0, "2026-10-05T00:00:00+00:00"),
        ],
        "architecture_ledger": [],
    })
    monkeypatch.setattr(review_repo, "_db", db)
    monkeypatch.setattr(ledger_module, "get_supabase", lambda: db)
    return db


@pytest.mark.asyncio
async def test_merge_writes_one_baseline_from_the_prs_last_completed_acs(db):
    from app.services.merge_baseline import record_merge_baseline
    await record_merge_baseline({}, "acme/widgets", 7, HEAD)
    rows = db.tables["architecture_ledger"]
    assert len(rows) == 1
    assert rows[0]["repo_full_name"] == "acme/widgets"
    assert rows[0]["acs_score"] == 85.0
    assert rows[0]["risk_scores"] == {"pr": 7, "sha": HEAD}


@pytest.mark.asyncio
async def test_running_the_job_twice_still_writes_one_row(db):
    from app.services.merge_baseline import record_merge_baseline
    await record_merge_baseline({}, "acme/widgets", 7, HEAD)
    await record_merge_baseline({}, "acme/widgets", 7, HEAD)
    assert len(db.tables["architecture_ledger"]) == 1


@pytest.mark.asyncio
async def test_no_completed_review_with_acs_means_no_baseline(db):
    from app.services.merge_baseline import record_merge_baseline
    await record_merge_baseline({}, "acme/widgets", 99, HEAD)
    assert db.tables["architecture_ledger"] == []


def test_record_merge_baseline_is_registered_on_the_worker():
    import app.worker as worker_module
    names = {f.name for f in worker_module.WorkerSettings.functions}
    assert {"run_review_job", "record_merge_baseline"} <= names


# --- the baseline is a median ---------------------------------------------------

def _ledger_rows(values):
    return [{"id": f"l{i}", "repo_full_name": "acme/widgets", "acs_score": v, "risk_scores": {"pr": i},
             "created_at": f"2026-10-{i + 1:02d}T00:00:00+00:00"} for i, v in enumerate(values)]


def test_baseline_is_the_median_of_the_last_10_rows(monkeypatch):
    # Oldest first. The last 10 are 50..95 (median 90.5); all 12 would give
    # 85.0, and the latest alone 95.0.
    values = [0.0, 0.0, 50.0, 60.0, 70.0, 80.0, 90.0, 91.0, 92.0, 93.0, 94.0, 95.0]
    db = FakeSupabase({"architecture_ledger": _ledger_rows(values) + [
        {"id": "x", "repo_full_name": "someone/else", "acs_score": 1.0, "risk_scores": {},
         "created_at": "2026-10-30T00:00:00+00:00"}]})
    monkeypatch.setattr(ledger_module, "get_supabase", lambda: db)
    assert LedgerRepository().get_baseline("acme/widgets")["acs_score"] == 90.5


def test_no_rows_means_no_baseline(monkeypatch):
    monkeypatch.setattr(ledger_module, "get_supabase", lambda: FakeSupabase({"architecture_ledger": []}))
    assert LedgerRepository().get_baseline("acme/widgets") is None


@pytest.mark.asyncio
async def test_regression_fires_against_the_median_not_the_latest_merge(monkeypatch):
    # Nine merges at 90 then one at 70: median 90, latest 70. A PR scoring
    # 75 is a regression against 90 (tolerance 5), not against 70.
    db = FakeSupabase({"architecture_ledger": _ledger_rows([90.0] * 9 + [70.0])})
    monkeypatch.setattr(ledger_module, "get_supabase", lambda: db)
    monkeypatch.setattr("app.graph.nodes.agent_3_critic.VectorStore", lambda: MagicMock(record_incident=AsyncMock()))
    monkeypatch.setattr(LedgerRepository, "get_consecutive_rejections", lambda self, p, r: 0)
    payload = ASTAnalyzerPayload(
        repo_full_name="acme/widgets", pr_number=1, changed_files=["a"], symbols=[],
        dependency_graph=[DependencyEdge(from_file="a", to_file="b", imported_symbols=[])] * 4,
    )
    state = ReviewState(repo_full_name="acme/widgets", pr_number=1, installation_id=1, ast_payload=payload, findings=[
        Finding(agent="agent_2a_struct", file_path="a", description="bad edge", severity="medium",
                dependency_edge_ref=("a", "b")),
    ])
    with patch("app.graph.nodes.agent_3_critic.get_llm_client",
               return_value=MagicMock(complete=AsyncMock(return_value="narrative"))):
        result = await agent_3_critic(state)
    assert result["acs_score"] == 75.0
    assert result["is_regression"] is True


@pytest.mark.asyncio
async def test_pipeline_shows_the_same_baseline_the_regression_flag_uses(fake_repos, mock_externals, mock_arq):
    fake_review_repo, _ = fake_repos
    res = await _post(_webhook_payload(), "open-1")
    event_payload, review_id, correlation_id = mock_arq.enqueue_job.call_args.args[1:4]
    with patch.object(LedgerRepository, "get_baseline", return_value={"acs_score": 90.5}):
        await run_review_job({}, event_payload, review_id, correlation_id)
    row = fake_review_repo.rows[review_id]
    assert row["previous_acs_score"] == 90.5
    assert row["regression"]["previousScore"] == 90.5
