"""
P2 "Auto-fix is chatty and 422s": every suggestion was its own inline
comment, and one on a line the PR didn't add made GitHub answer 422. Now
auto-fix posts one pr.create_review(commit=head, event="COMMENT", ...) per
head SHA; only suggestions on added lines (from the parsed diff hunks) are
inline comments, and the rest go in the review body as text.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.graph.state import Finding, ReviewState
from app.schemas.ast_payload import ASTAnalyzerPayload

DIFF = """diff --git a/src/a.ts b/src/a.ts
index 1111111..2222222 100644
--- a/src/a.ts
+++ b/src/a.ts
@@ -1,3 +1,4 @@
 const keep = 1;
-const old = 2;
+const added = 2;
+const alsoAdded = 3;
 const tail = 4;
@@ -10,0 +12,1 @@ function f() {
+  return null;
diff --git a/src/new.ts b/src/new.ts
new file mode 100644
--- /dev/null
+++ b/src/new.ts
@@ -0,0 +1,2 @@
+export const x = 1;
+export const y = 2;
diff --git a/src/gone.ts b/src/gone.ts
deleted file mode 100644
--- a/src/gone.ts
+++ /dev/null
@@ -1 +0,0 @@
-bye
"""


def test_added_lines_come_from_the_hunks():
    from app.services.diff_lines import added_lines
    assert added_lines(DIFF) == {"src/a.ts": {2, 3, 12}, "src/new.ts": {1, 2}}
    assert added_lines("") == {}


def _finding(file_path, line, patch="fixed()", severity="medium"):
    return Finding(agent="agent_2b_chaos", file_path=file_path, line=line, description="issue",
                   severity=severity, suggested_patch=patch)


def _state(findings, diff=DIFF):
    return ReviewState(
        repo_full_name="acme/widgets", pr_number=42, installation_id=12345, head_sha="h" * 40,
        diff_text=diff, verified_findings=findings,
        ast_payload=ASTAnalyzerPayload(repo_full_name="acme/widgets", pr_number=42, changed_files=[],
                                       symbols=[], dependency_graph=[], hard_rule_violations=[]),
    )


async def _run(findings, client=None):
    from app.graph.nodes.agent_4_autofix import agent_4_autofix
    client = client or MagicMock()
    with patch("app.services.github_client.GitHubClient", return_value=client):
        result = await agent_4_autofix(_state(findings))
    return result, client


@pytest.mark.asyncio
async def test_one_review_with_inline_suggestions_on_added_lines_only():
    result, client = await _run([
        _finding("src/a.ts", 2, "const added = 20;"),       # added line
        _finding("src/new.ts", 1, "export const x = 10;"),  # added line in a new file
        _finding("src/a.ts", 1, "const keep = 10;"),        # context line: not added
        _finding("src/other.ts", 5, "other()"),             # file not in the diff
    ])
    client.post_suggestion_review.assert_called_once()
    kwargs = client.post_suggestion_review.call_args.kwargs
    assert (kwargs["repo_full_name"], kwargs["pr_number"], kwargs["head_sha"]) == ("acme/widgets", 42, "h" * 40)
    assert [(c["path"], c["line"], c["side"]) for c in kwargs["comments"]] == [
        ("src/a.ts", 2, "RIGHT"), ("src/new.ts", 1, "RIGHT")]
    assert kwargs["comments"][0]["body"] == "```suggestion\nconst added = 20;\n```"
    # The other two are in the review body as text, not inline.
    assert "`src/a.ts:1`" in kwargs["body"] and "`src/other.ts:5`" in kwargs["body"]
    assert "const keep = 10;" in kwargs["body"] and "other()" in kwargs["body"]
    assert result == {"autofix_posted": 2, "autofix_failed": 0}
    client.post_inline_suggestion.assert_not_called()


@pytest.mark.asyncio
async def test_conflicts_still_resolve_to_one_suggestion_per_line():
    result, client = await _run([_finding("src/a.ts", 3, "low()", "low"), _finding("src/a.ts", 3, "crit()", "critical")])
    comments = client.post_suggestion_review.call_args.kwargs["comments"]
    assert [c["body"] for c in comments] == ["```suggestion\ncrit()\n```"]
    assert result == {"autofix_posted": 1, "autofix_failed": 0}


@pytest.mark.asyncio
async def test_a_failed_review_post_is_counted_not_raised():
    client = MagicMock()
    client.post_suggestion_review.side_effect = RuntimeError("GitHub 422")
    result, _ = await _run([_finding("src/a.ts", 2), _finding("src/new.ts", 2)], client)
    assert result == {"autofix_posted": 0, "autofix_failed": 2}


@pytest.mark.asyncio
async def test_nothing_patchable_posts_nothing():
    result, client = await _run([_finding("src/a.ts", 2, patch=None)])
    client.post_suggestion_review.assert_not_called()
    assert result == {"autofix_posted": 0, "autofix_failed": 0}


def _github_client(existing_reviews):
    from app.services.github_client import GitHubClient
    gh = GitHubClient.__new__(GitHubClient)
    gh._client = MagicMock()
    pr = gh._client.get_repo.return_value.get_pull.return_value
    pr.get_reviews.return_value = existing_reviews
    return gh, pr


def _review(login, commit_id, body):
    r = MagicMock()
    r.user.login, r.commit_id, r.body = login, commit_id, body
    return r


def test_the_client_posts_one_comment_review_on_the_head_commit():
    gh, pr = _github_client([])
    comments = [{"path": "src/a.ts", "line": 2, "side": "RIGHT", "body": "```suggestion\nx\n```"}]
    assert gh.post_suggestion_review(repo_full_name="acme/widgets", pr_number=42, head_sha="h" * 40,
                                     body="Suggested fixes", comments=comments, bot_login="ignition[bot]") is True
    kwargs = pr.create_review.call_args.kwargs
    assert kwargs["event"] == "COMMENT" and kwargs["comments"] == comments
    assert kwargs["commit"] is gh._client.get_repo.return_value.get_commit.return_value
    gh._client.get_repo.return_value.get_commit.assert_called_once_with("h" * 40)
    assert kwargs["body"].startswith("<!-- ignition:suggestions -->")


def test_the_client_posts_at_most_one_review_per_head_sha():
    from app.services.github_client import GitHubClient  # noqa: F401
    gh, pr = _github_client([_review("ignition[bot]", "h" * 40, "<!-- ignition:suggestions -->\nSuggested fixes")])
    assert gh.post_suggestion_review(repo_full_name="acme/widgets", pr_number=42, head_sha="h" * 40,
                                     body="Suggested fixes", comments=[], bot_login="ignition[bot]") is False
    pr.create_review.assert_not_called()
    # A review on an older commit, or someone else's, doesn't count.
    gh, pr = _github_client([_review("ignition[bot]", "o" * 40, "<!-- ignition:suggestions -->"),
                             _review("someone", "h" * 40, "<!-- ignition:suggestions -->")])
    assert gh.post_suggestion_review(repo_full_name="acme/widgets", pr_number=42, head_sha="h" * 40,
                                     body="b", comments=[], bot_login="ignition[bot]") is True
