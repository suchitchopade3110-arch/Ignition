"""
PyGithub wrapper: posts the structured review comment (+ any auto-fix
patches) to the PR thread. No other module should import PyGithub directly.

Uses proper GitHub App authentication: the raw private key signs a
short-lived JWT (via Auth.AppAuth), which is then exchanged for a
scoped installation access token (via GithubIntegration). The private
key itself is NEVER used directly as an API token/header value.
"""
from github import Auth, GithubIntegration

from app.config import get_settings


class GitHubClient:
    def __init__(self, installation_id: int):
        settings = get_settings()
        auth = Auth.AppAuth(
            app_id=settings.github_app_id,
            private_key=settings.github_private_key,
        )
        integration = GithubIntegration(auth=auth)
        # Exchanges the App's JWT for a real, scoped installation token —
        # this is the actual authenticated client, not the raw key.
        self._client = integration.get_github_for_installation(installation_id)

    def post_review_comment(self, repo_full_name: str, pr_number: int, markdown_body: str) -> None:
        repo = self._client.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)
        pr.create_issue_comment(markdown_body)

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