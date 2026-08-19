"""
Coverage for app.main._handle_installation_event — "installation" and
"installation_repositories" webhook events used to be acknowledged but
never acted on; this exercises the actual repo register/deregister logic.
"""
import hashlib
import hmac
import json
from unittest.mock import MagicMock

import httpx
import pytest

import app.main as main_module
from app.config import get_settings
from app.services.review_pipeline import repo_repo


def _sign(body: bytes) -> str:
    secret = get_settings().github_webhook_secret
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture
def fake_repo_repo(monkeypatch):
    fake = MagicMock()
    monkeypatch.setattr(repo_repo, "get_or_create_repo", fake.get_or_create_repo)
    monkeypatch.setattr(repo_repo, "set_repo_installed", fake.set_repo_installed)
    return fake


async def _post_webhook(body: bytes, event: str, delivery: str) -> httpx.Response:
    signature = _sign(body)
    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(
            "/webhooks/github", content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": signature,
                "X-GitHub-Delivery": delivery,
                "X-GitHub-Event": event,
            },
        )


@pytest.mark.asyncio
async def test_installation_created_registers_repos(fake_repo_repo):
    payload = {
        "action": "created",
        "installation": {"id": 42},
        "repositories": [{"full_name": "acme/widgets"}, {"full_name": "acme/gadgets"}],
    }
    response = await _post_webhook(json.dumps(payload).encode(), "installation", "install-created-1")

    assert response.status_code == 202
    assert response.json() == {"status": "processed", "event": "installation"}
    assert fake_repo_repo.get_or_create_repo.call_count == 2
    fake_repo_repo.get_or_create_repo.assert_any_call("acme/widgets")
    fake_repo_repo.set_repo_installed.assert_any_call("acme/widgets", True)
    fake_repo_repo.set_repo_installed.assert_any_call("acme/gadgets", True)


@pytest.mark.asyncio
async def test_installation_deleted_deregisters_repos_without_deleting_data(fake_repo_repo):
    payload = {
        "action": "deleted",
        "installation": {"id": 42},
        "repositories": [{"full_name": "acme/widgets"}],
    }
    response = await _post_webhook(json.dumps(payload).encode(), "installation", "install-deleted-1")

    assert response.status_code == 202
    fake_repo_repo.set_repo_installed.assert_called_once_with("acme/widgets", False)
    # Deregistering must never call get_or_create_repo — uninstall doesn't
    # create rows for repos this app never saw.
    fake_repo_repo.get_or_create_repo.assert_not_called()


@pytest.mark.asyncio
async def test_installation_repositories_added_and_removed(fake_repo_repo):
    payload = {
        "action": "added",
        "installation": {"id": 42},
        "repositories_added": [{"full_name": "acme/new-repo"}],
        "repositories_removed": [{"full_name": "acme/old-repo"}],
    }
    response = await _post_webhook(json.dumps(payload).encode(), "installation_repositories", "install-repos-1")

    assert response.status_code == 202
    fake_repo_repo.get_or_create_repo.assert_called_once_with("acme/new-repo")
    fake_repo_repo.set_repo_installed.assert_any_call("acme/new-repo", True)
    fake_repo_repo.set_repo_installed.assert_any_call("acme/old-repo", False)


@pytest.mark.asyncio
async def test_installation_suspend_action_deregisters(fake_repo_repo):
    payload = {
        "action": "suspend",
        "installation": {"id": 42},
        "repositories": [{"full_name": "acme/widgets"}],
    }
    response = await _post_webhook(json.dumps(payload).encode(), "installation", "install-suspend-1")

    assert response.status_code == 202
    fake_repo_repo.set_repo_installed.assert_called_once_with("acme/widgets", False)


@pytest.mark.asyncio
async def test_installation_unknown_action_is_a_noop(fake_repo_repo):
    payload = {"action": "new_permissions_accepted", "installation": {"id": 42}}
    response = await _post_webhook(json.dumps(payload).encode(), "installation", "install-noop-1")

    assert response.status_code == 202
    fake_repo_repo.get_or_create_repo.assert_not_called()
    fake_repo_repo.set_repo_installed.assert_not_called()
