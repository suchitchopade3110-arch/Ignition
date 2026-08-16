"""
PyGithub wrapper: posts the structured review comment (+ any auto-fix
patches) to the PR thread. No other module should import PyGithub directly.

Uses proper GitHub App authentication: the raw private key signs a
short-lived JWT (via Auth.AppAuth), which is then exchanged for a
scoped installation access token (via GithubIntegration). The private
key itself is NEVER used directly as an API token/header value.

Installation access tokens (NOT the JWT — the JWT stays short-lived/
generated fresh every time, per GitHub's own model) are cached in Redis,
keyed by installation_id, with a TTL matching the token's real expires_at
from GitHub minus a 5-minute safety margin. Every call site constructs a
fresh GitHubClient per operation (see the call sites in app/main.py,
app/graph/nodes/, app/services/review_pipeline.py), which before this
cache meant a fresh JWT-for-installation-token exchange on every single
one of them, even multiple times within the same review run.
"""
import logging
from datetime import datetime, timezone

from github import Auth, GithubIntegration

from app.config import get_settings
from app.services.redis_client import get_sync_redis

logger = logging.getLogger(__name__)

_TOKEN_REFRESH_MARGIN_SECONDS = 300  # refresh if less than 5 min would remain


def _cache_key(installation_id: int) -> str:
    return f"gh_installation_token:{installation_id}"


class GitHubClient:
    def __init__(self, installation_id: int):
        redis = get_sync_redis()
        cache_key = _cache_key(installation_id)

        cached_token = redis.get(cache_key)
        if cached_token:
            logger.info("Reused cached installation token", extra={"installation_id": installation_id})
            self._client = self._build_github(cached_token)
            return

        settings = get_settings()
        auth = Auth.AppAuth(
            app_id=settings.github_app_id,
            private_key=settings.github_private_key,
        )
        integration = GithubIntegration(auth=auth)
        # Exchanges the App's JWT for a real, scoped installation token.
        # get_access_token (not get_github_for_installation) is used
        # specifically because it hands back the raw token + its real
        # expires_at, which is what the cache needs — a Github client
        # object alone doesn't expose either.
        authorization = integration.get_access_token(installation_id)
        token = authorization.token
        expires_at = authorization.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        ttl_seconds = int((expires_at - datetime.now(timezone.utc)).total_seconds()) - _TOKEN_REFRESH_MARGIN_SECONDS
        if ttl_seconds > 0:
            redis.setex(cache_key, ttl_seconds, token)
        logger.info("Exchanged fresh installation token", extra={
            "installation_id": installation_id, "cached_ttl_seconds": max(ttl_seconds, 0),
        })

        self._client = self._build_github(token)

    @staticmethod
    def _build_github(token: str):
        from github import Github
        return Github(auth=Auth.Token(token))

    def post_review_comment(self, repo_full_name: str, pr_number: int, markdown_body: str) -> dict:
        repo = self._client.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)
        comment = pr.create_issue_comment(markdown_body)
        # raw_data is the actual JSON GitHub's API returned for this
        # comment (id, html_url, etc.) — callers that need to prove the
        # comment landed on the right PR should use this, not just a
        # "posted successfully" log line. Logged here (not just at each
        # call site) so every caller gets this for free — the actual
        # comment body/markdown is deliberately not logged, only metadata.
        logger.info("GitHub review comment posted", extra={
            "repo_full_name": repo_full_name, "pr_number": pr_number,
            "comment_id": comment.raw_data.get("id"), "comment_url": comment.raw_data.get("html_url"),
        })
        return comment.raw_data

    def post_inline_suggestion(
        self, repo_full_name: str, pr_number: int, file_path: str, line: int, patch: str
    ) -> None:
        """Posts an auto-fix suggestion as an inline review comment."""
        repo = self._client.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)
        commit = repo.get_commit(pr.head.sha)
        pr.create_review_comment(
            body=f"```suggestion\n{patch}\n```",
            commit=commit,
            path=file_path,
            line=line,
        )

    def get_pr_diff(self, repo_full_name: str, pr_number: int) -> str:
        """
        Fetches the unified diff text for a PR — the actual code changes,
        not just structural metadata. This is what gives the semantic
        agents (2A, 2B, 2C-phase-2) real code to review instead of only
        symbol names and import graphs.
        """
        repo = self._client.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)
        # PyGithub doesn't expose diff text directly; fetch it via the
        # authenticated requester using the PR's diff_url-equivalent API.
        headers, data = self._client._Github__requester.requestBlobAndCheck(
            "GET", pr.url, headers={"Accept": "application/vnd.github.v3.diff"}
        )
        if isinstance(data, dict):
            return data.get("data", "")
        return data