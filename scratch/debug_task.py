import asyncio
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.schemas.github import PullRequestWebhook
from app.main import run_review_stream_task
from app.config import get_settings
from github import Auth, GithubIntegration

settings = get_settings()
auth = Auth.AppAuth(settings.github_app_id, settings.github_private_key)
integration = GithubIntegration(auth=auth)
inst_id = integration.get_installations()[0].id

event_data = {
    "action": "synchronize",
    "repository": {
        "full_name": "suchitchopade3110-arch/Ignition",
        "default_branch": "main",
        "clone_url": "https://github.com/suchitchopade3110-arch/Ignition.git"
    },
    "pull_request": {
        "number": 4,
        "diff_url": "https://github.com/suchitchopade3110-arch/Ignition/pull/4.diff",
        "head": {"sha": "3f499fdc85440e0870bdef8560d0439f57b715e0"},
        "base": {"sha": "b7dd337something"}
    },
    "installation": {"id": inst_id} 
}

event = PullRequestWebhook.model_validate(event_data)
review_id = "4d49aa80-4188-40ed-804f-8620f6a7c171"

async def main():
    try:
        await run_review_stream_task(event, review_id)
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
