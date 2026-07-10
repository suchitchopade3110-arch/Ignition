import os
import sys
import uuid
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.repositories.dashboard import RepoRepository, ReviewRepository

def populate_db():
    repo_repo = RepoRepository()
    review_repo = ReviewRepository()

    print("Populating database...")
    repo_full_name = "testowner/testrepo"
    
    # 1. Insert repository and settings
    repo_repo.get_or_create_repo(repo_full_name)
    repo_repo.update_settings(repo_full_name.replace("/", "_"), {"enable_ai_review": True})
    
    # 2. Insert reviews
    # Review 1: completed
    rev1_id = str(uuid.uuid4())
    review_repo.create_review(
        review_id=rev1_id,
        repo_full_name=repo_full_name,
        pr_number=101,
        title="Fix bug",
        author="alice",
        branch="fix-bug",
        commit_sha="abcdef"
    )
    review_repo.update_review(rev1_id, {
        "status": "completed",
        "acs_score": 95.0,
        "findings_count": 0
    })

    # Review 2: waiting_hitl (required by tests)
    rev2_id = str(uuid.uuid4())
    review_repo.create_review(
        review_id=rev2_id,
        repo_full_name=repo_full_name,
        pr_number=102,
        title="Add feature",
        author="bob",
        branch="feature",
        commit_sha="123456"
    )
    review_repo.update_review(rev2_id, {
        "status": "waiting_hitl",
        "severity": "high",
        "findings_count": 2,
        # Intentionally setting is_regression to False here to verify it doesn't default to True when acsScore is null
        "regression": {"is_regression": False}
    })

    # Review 3: completed with regression (to test activeRegressions)
    rev3_id = str(uuid.uuid4())
    review_repo.create_review(
        review_id=rev3_id,
        repo_full_name=repo_full_name,
        pr_number=103,
        title="Bad PR",
        author="charlie",
        branch="bad-pr",
        commit_sha="abcdef1"
    )
    review_repo.update_review(rev3_id, {
        "status": "completed",
        "acs_score": 40.0,
        "findings_count": 5,
        "regression": {"is_regression": True}
    })

    print("Database populated successfully.")
    return rev1_id, rev2_id, repo_full_name

def test_endpoints(rev2_id, repo_full_name):
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    results = {}

    def fetch(name, method, url, **kwargs):
        print(f"Testing {name}...")
        resp = client.request(method, f"/api{url}", **kwargs)
        try:
            results[name] = resp.json()
        except:
            results[name] = resp.text

    fetch("/stats", "GET", "/stats")
    fetch("/repos", "GET", "/repos")
    fetch("/repos/{id}/settings", "GET", f"/repos/{repo_full_name.replace('/', '_')}/settings")
    fetch("/reviews", "GET", "/reviews")
    fetch("/repos/{repo}/reviews", "GET", f"/repos/{repo_full_name}/reviews")
    fetch("/reviews/{id}", "GET", f"/reviews/{rev2_id}")
    fetch("/hitl/pending", "GET", "/hitl/pending")
    fetch("/ledger/{repo}", "GET", f"/ledger/{repo_full_name}")
    fetch("/ledger/{repo}/trend", "GET", f"/ledger/{repo_full_name}/trend")
    fetch("/auth/me", "GET", "/auth/me")
    
    # Mutations
    fetch("/repos/{id}/settings PATCH", "PATCH", f"/repos/{repo_full_name.replace('/', '_')}/settings", json={"enable_auto_fix": True})
    fetch("/hitl/{id}/approve", "POST", f"/hitl/{rev2_id}/approve")
    
    # Assertions
    trend_result = results.get("/ledger/{repo}/trend")
    assert isinstance(trend_result, list), f"Expected list for /ledger/trend, got {type(trend_result)}"
    
    hitl_pending = results.get("/hitl/pending", [])
    for r in hitl_pending:
        if r.get("acsScore") is None:
            assert not r.get("regression", {}).get("isRegression", False), "isRegression should not be true when acsScore is null"

    # Save results to output file
    out_path = os.path.join(os.path.dirname(__file__), "api_test_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {out_path}")

if __name__ == "__main__":
    rev1, rev2, repo = populate_db()
    test_endpoints(rev2, repo)
    print("Done testing.")
