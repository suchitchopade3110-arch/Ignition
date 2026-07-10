import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import uuid
import time
from app.config import get_settings
from github import Auth, GithubIntegration, Github

settings = get_settings()
auth = Auth.AppAuth(settings.github_app_id, settings.github_private_key)
integration = GithubIntegration(auth=auth)

inst_id = integration.get_installations()[0].id
access_token = integration.get_access_token(inst_id).token

g = Github(access_token)
repo = g.get_repo("suchitchopade3110-arch/Ignition")

branch_name = "test-e2e-2"

# Create PR
pr = repo.create_pull(
    title=f"E2E Test PR {branch_name}",
    body="This PR is automatically created to test the end-to-end pipeline.",
    head=branch_name,
    base="main"
)

print(f"CREATED_PR={pr.number}")
print(f"PR_URL={pr.html_url}")
