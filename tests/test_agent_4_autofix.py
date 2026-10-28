"""
agent_4_autofix is the one node in the graph that writes to GitHub outside
the final review comment — it posts one review of `suggestion` comments —
so a bug here shows up as junk pushed onto someone's real PR, not just a
wrong dashboard value. It had zero test coverage before this file.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.graph.nodes.agent_4_autofix import agent_4_autofix, _detect_line_conflicts, _resolve_conflict
from app.graph.state import Finding, ReviewState
from app.schemas.ast_payload import ASTAnalyzerPayload


def _finding(file_path="a.ts", line=10, severity="medium", patch="fixed()", agent="agent_2a_struct"):
    return Finding(
        agent=agent, file_path=file_path, line=line, description="issue",
        severity=severity, suggested_patch=patch,
    )


# Lines 1-9 of a.ts and b.ts are added by the PR, so suggestions on them can
# be inline (solutions doc, P2 auto-fix: inline only on added lines).
DIFF = "".join(
    f"diff --git a/{p} b/{p}\n--- a/{p}\n+++ b/{p}\n@@ -0,0 +1,9 @@\n" + "+x\n" * 9 for p in ("a.ts", "b.ts")
)


def _make_state(verified_findings: list[Finding]) -> ReviewState:
    return ReviewState(
        repo_full_name="acme/widgets",
        pr_number=42,
        installation_id=12345,
        diff_text=DIFF,
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets", pr_number=42,
            changed_files=[], symbols=[], dependency_graph=[], hard_rule_violations=[],
        ),
        verified_findings=verified_findings,
    )


class TestDetectLineConflicts:
    def test_no_conflict_when_locations_differ(self):
        findings = [_finding(line=10), _finding(line=20)]
        assert _detect_line_conflicts(findings) == {}

    def test_findings_without_a_patch_or_line_are_ignored(self):
        findings = [
            _finding(line=10, patch=None),
            Finding(agent="a", file_path="a.ts", line=None, description="x", severity="low",
                    suggested_patch="p"),
        ]
        assert _detect_line_conflicts(findings) == {}

    def test_two_findings_at_same_file_line_conflict(self):
        f1, f2 = _finding(line=10), _finding(line=10)
        conflicts = _detect_line_conflicts([f1, f2])
        assert conflicts == {"a.ts:10": [f1, f2]}


class TestResolveConflict:
    def test_highest_severity_wins(self):
        low, critical = _finding(severity="low"), _finding(severity="critical")
        assert _resolve_conflict([low, critical]) is critical

    def test_tie_at_same_severity_is_deterministic(self):
        # max() on a tie returns the first max-valued element — pin that
        # behavior explicitly so a future refactor can't silently flip it
        # to "last wins" without a test noticing.
        first, second = _finding(severity="high"), _finding(severity="high")
        assert _resolve_conflict([first, second]) is first


class TestAgentAutofix:
    @pytest.mark.asyncio
    async def test_no_patchable_findings_short_circuits_without_a_github_call(self):
        state = _make_state([_finding(patch=None)])
        with patch("app.services.github_client.GitHubClient") as mock_client_cls:
            result = await agent_4_autofix(state)
        mock_client_cls.assert_not_called()
        assert result == {"autofix_posted": 0, "autofix_failed": 0}

    @pytest.mark.asyncio
    async def test_posts_one_suggestion_per_non_conflicting_finding(self):
        state = _make_state([_finding(file_path="a.ts", line=1), _finding(file_path="b.ts", line=2)])
        mock_client = MagicMock()
        with patch("app.services.github_client.GitHubClient", return_value=mock_client):
            result = await agent_4_autofix(state)

        assert result == {"autofix_posted": 2, "autofix_failed": 0}
        # One review carrying both suggestions (solutions doc, P2 auto-fix).
        mock_client.post_suggestion_review.assert_called_once()
        assert len(mock_client.post_suggestion_review.call_args.kwargs["comments"]) == 2

    @pytest.mark.asyncio
    async def test_conflicting_findings_at_the_same_location_post_only_the_resolved_one(self):
        low = _finding(file_path="a.ts", line=5, severity="low", patch="patch-low")
        critical = _finding(file_path="a.ts", line=5, severity="critical", patch="patch-critical")
        state = _make_state([low, critical])
        mock_client = MagicMock()

        with patch("app.services.github_client.GitHubClient", return_value=mock_client):
            result = await agent_4_autofix(state)

        assert result == {"autofix_posted": 1, "autofix_failed": 0}
        assert mock_client.post_suggestion_review.call_args.kwargs["comments"] == [
            {"path": "a.ts", "line": 5, "side": "RIGHT", "body": "```suggestion\npatch-critical\n```"},
        ]

    @pytest.mark.asyncio
    async def test_a_failed_post_is_counted_and_does_not_abort_the_review(self):
        # One review now (solutions doc, P2 auto-fix), so a failed post
        # counts every suggestion in it as failed, and never raises.
        state = _make_state([_finding(file_path="a.ts", line=1), _finding(file_path="b.ts", line=2)])
        mock_client = MagicMock()
        mock_client.post_suggestion_review.side_effect = Exception("GitHub 422")

        with patch("app.services.github_client.GitHubClient", return_value=mock_client):
            result = await agent_4_autofix(state)

        assert result == {"autofix_posted": 0, "autofix_failed": 2}
        assert mock_client.post_suggestion_review.call_count == 1
