"""
Inbound GitHub webhook payload contract.

Kept separate from ast_payload.py deliberately: this schema evolves on
GitHub's timeline, the AST schema evolves on ours. Merging them into one
schemas.py would hide that these are two independently-drifting contracts.
"""
from pydantic import BaseModel


class Repository(BaseModel):
    full_name: str
    default_branch: str
    clone_url: str  # public HTTPS git URL — what the AST analyzer clones from

class CommitRef(BaseModel):
    sha: str

class PullRequestPayload(BaseModel):
    number: int
    diff_url: str
    head: CommitRef
    base: CommitRef

    @property
    def head_sha(self):
        return self.head.sha

    @property
    def base_sha(self):
        return self.base.sha

class InstallationRef(BaseModel):
    id: int


class PullRequestWebhook(BaseModel):
    action: str  # "opened" | "synchronize" | "reopened" | ...
    repository: Repository
    pull_request: PullRequestPayload
    installation: InstallationRef