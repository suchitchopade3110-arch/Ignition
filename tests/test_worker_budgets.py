"""
I-7: Arq's defaults (10 jobs, 300 s) and a 60 s budget that only covered
the graph. Now WORKER_MAX_JOBS (default 2), job_timeout 240, and the whole
job — clone, analysis and graph — inside asyncio.timeout(220), below
Arq's limit, ending as a recorded "timed out" review (not Arq killing it).
"""
import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

import app.services.review_pipeline as pipeline
from app.services.review_pipeline import run_review_job
from tests.test_check_runs import _enqueue
from tests.test_integration_webhook_review_comment import (  # noqa: F401  (fixtures)
    fake_repos, mock_arq, mock_externals,
)

REPO = Path(__file__).resolve().parents[1]


def _worker_setting(name: str, env: dict) -> str:
    code = f"import app.worker as w; print(w.WorkerSettings.{name})"
    full_env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
    full_env.update({"GITHUB_APP_ID": "1", "LLM_API_KEY": "x", "SUPABASE_URL": "https://d.supabase.co",
                     "SUPABASE_SERVICE_KEY": "x", **env})
    full_env.pop("WORKER_MAX_JOBS", None) if "WORKER_MAX_JOBS" not in env else None
    out = subprocess.run([sys.executable, "-c", code], cwd=REPO, env=full_env, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr[-800:]
    return out.stdout.strip().splitlines()[-1]


def test_two_jobs_per_worker_by_default_and_configurable():
    assert _worker_setting("max_jobs", {}) == "2"
    assert _worker_setting("max_jobs", {"WORKER_MAX_JOBS": "5"}) == "5"


def test_arq_timeout_sits_above_the_whole_job_budget():
    from app.worker import WorkerSettings
    assert WorkerSettings.job_timeout == 240
    assert pipeline.JOB_BUDGET_SECONDS == 220 < WorkerSettings.job_timeout


async def _run_with_budget(budget, fake_repos, mock_externals, mock_arq, **patches):
    fake_review_repo, _ = fake_repos
    event_payload, review_id, correlation_id = await _enqueue(mock_arq)
    with patch.object(pipeline, "JOB_BUDGET_SECONDS", budget, create=True):
        started = time.monotonic()
        await run_review_job({}, event_payload, review_id, correlation_id)  # returns; no exception
        elapsed = time.monotonic() - started
    return fake_review_repo.rows[review_id], mock_externals["github_instance"].complete_check_run, elapsed


@pytest.mark.asyncio
async def test_a_slow_analysis_is_cut_off_by_the_whole_job_budget(fake_repos, mock_externals, mock_arq):
    async def slow_analysis(*a, **k):
        await asyncio.sleep(5)  # the graph's own 60 s budget never starts
    with patch.object(pipeline.ast_client, "analyze_git", new=slow_analysis):
        row, complete, elapsed = await _run_with_budget(0.3, fake_repos, mock_externals, mock_arq)
    assert elapsed < 2
    assert row["status"] == "failed" and row["status_reason"].startswith("timed out — exceeded the job budget")
    kwargs = complete.call_args.kwargs
    assert kwargs["conclusion"] == "neutral" and kwargs["title"].startswith("Ignition could not finish: timed out")


@pytest.mark.asyncio
async def test_the_budget_also_covers_the_steps_before_analysis(fake_repos, mock_externals, mock_arq):
    gh = mock_externals["github_instance"]

    def slow_pr_fetch(*a, **k):
        time.sleep(1.0)  # a hung GitHub call, before the analysis even starts
        return "diff --git a/x b/x\n"
    gh.get_pr_diff.side_effect = slow_pr_fetch
    row, complete, elapsed = await _run_with_budget(0.3, fake_repos, mock_externals, mock_arq)
    assert elapsed < 1.0
    assert row["status"] == "failed" and row["status_reason"].startswith("timed out — exceeded the job budget")
    assert complete.call_args.kwargs["conclusion"] == "neutral"


def test_render_runs_two_jobs_per_worker():
    import yaml
    services = {s["name"]: s for s in yaml.safe_load((REPO / "render.yaml").read_text())["services"]}
    assert {"key": "WORKER_MAX_JOBS", "value": "2"} in services["ignition-worker"]["envVars"]
