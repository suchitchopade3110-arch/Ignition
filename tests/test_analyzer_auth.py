"""
Audit P0-8 (private repos): the AST analyzer used to clone anonymously.
The worker now hands it the installation token — in the request body,
never in a URL — and GitHubClient exposes that token whichever way it
was obtained (Redis cache hit or a fresh JWT exchange).
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import github_client as github_client_module
from app.services.ast_client import ASTClient
from app.services.github_client import GitHubClient


def _payload_json():
    return {
        "repo_full_name": "acme/private", "pr_number": 3, "changed_files": [], "symbols": [],
        "dependency_graph": [], "hard_rule_violations": [], "changed_packages": [],
    }


@pytest.mark.asyncio
async def test_ast_client_sends_installation_token_in_body_not_url():
    response = MagicMock(json=MagicMock(return_value=_payload_json()), raise_for_status=MagicMock())
    post = AsyncMock(return_value=response)
    with patch("httpx.AsyncClient.post", new=post):
        await ASTClient(base_url="http://ast:4000").analyze_git(
            repo_full_name="acme/private", pr_number=3, clone_url="https://github.com/acme/private.git",
            ref="h" * 40, base_ref="b" * 40, auth_token="ghs_SECRET",
        )
        await ASTClient(base_url="http://ast:4000").analyze_git(
            repo_full_name="acme/private", pr_number=3, clone_url="https://github.com/acme/private.git",
            ref="h" * 40, base_ref="b" * 40,
        )
    with_token, without_token = post.await_args_list
    assert with_token.args[0] == "http://ast:4000/analyze"
    assert with_token.kwargs["json"]["auth_token"] == "ghs_SECRET"
    assert "ghs_SECRET" not in with_token.kwargs["json"]["source"]["url"]
    assert "auth_token" not in without_token.kwargs["json"]


def test_installation_token_is_exposed_on_cache_hit_and_on_fresh_exchange():
    cached = MagicMock(get=MagicMock(return_value="ghs_cached"))
    with patch.object(github_client_module, "get_sync_redis", return_value=cached), \
         patch.object(GitHubClient, "_build_github", return_value=MagicMock()):
        assert GitHubClient(installation_id=1).installation_token == "ghs_cached"

    empty = MagicMock(get=MagicMock(return_value=None))
    auth = MagicMock(token="ghs_fresh", expires_at=datetime.now(timezone.utc) + timedelta(hours=1))
    integration = MagicMock(get_access_token=MagicMock(return_value=auth))
    with patch.object(github_client_module, "get_sync_redis", return_value=empty), \
         patch.object(github_client_module, "GithubIntegration", return_value=integration), \
         patch.object(github_client_module.Auth, "AppAuth"), \
         patch.object(GitHubClient, "_build_github", return_value=MagicMock()):
        assert GitHubClient(installation_id=1).installation_token == "ghs_fresh"
