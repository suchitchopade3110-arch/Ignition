"""
PyGithub wrapper: posts the structured review comment (+ any auto-fix
patches) to the PR thread. No other module should import PyGithub directly.
"""
from github import Github

from app.config import get_settings


class GitHubClient:
    def __init__(self):
        settings = get_settings()
        self._client = Github(settings.github_private_key)

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