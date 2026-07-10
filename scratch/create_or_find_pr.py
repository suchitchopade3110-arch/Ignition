import sys
sys.path.append('.')
import os
from github import Auth, GithubIntegration
from app.config import get_settings

settings = get_settings()
auth = Auth.AppAuth(
    app_id=settings.github_app_id,
    private_key=settings.github_private_key,
)
integration = GithubIntegration(auth=auth)

installations = integration.get_installations()
print(f"Installations: {[i.id for i in installations]}")
inst_id = installations[0].id

gh = integration.get_github_for_installation(inst_id)
repo = gh.get_repo("suchitchopade3110-arch/Ignition")

open_prs = list(repo.get_pulls(state='open'))
print(f"Open PRs: {[(p.number, p.head.ref, p.base.ref) for p in open_prs]}")

target_pr = None
for pr in open_prs:
    if pr.head.ref == 'test-embed-n1':
        target_pr = pr
        print(f"Found existing PR #{pr.number} for test-embed-n1")
        break

if not target_pr:
    print("Creating new PR for test-embed-n1...")
    target_pr = repo.create_pull(
        title="Test Embed N+1 query",
        body="N+1 query test fixture",
        head="test-embed-n1",
        base="main"
    )
    print(f"Created PR #{target_pr.number}")

print(f"CONFIRMED_PR_NUMBER={target_pr.number}")
print(f"CONFIRMED_HEAD_SHA={target_pr.head.sha}")
print(f"CONFIRMED_BASE_SHA={target_pr.base.sha}")
