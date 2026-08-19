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
    # `ref` (the branch name) is only present on `head`/`base` in real
    # GitHub payloads for pull_request events, but modeling it as optional
    # here (rather than a second slimmer CommitRef variant) keeps this one
    # schema usable for both — head.ref is what main.py actually needs.
    ref: str | None = None

class PullRequestUser(BaseModel):
    login: str

class PullRequestPayload(BaseModel):
    number: int
    diff_url: str
    head: CommitRef
    base: CommitRef
    # Was missing entirely — main.py used to hardcode author="unknown"
    # rather than reading it from here because there was nowhere to read
    # it from. Optional so payloads that genuinely omit it (hand-crafted
    # test fixtures, mainly) don't fail validation.
    user: PullRequestUser | None = None

    @property
    def head_sha(self):
        return self.head.sha

    @property
    def base_sha(self):
        return self.base.sha

    @property
    def author_login(self) -> str:
        return self.user.login if self.user else "unknown"

    @property
    def head_branch(self) -> str:
        return self.head.ref or "unknown"

class InstallationRef(BaseModel):
    id: int


class PullRequestWebhook(BaseModel):
    action: str  # "opened" | "synchronize" | "reopened" | ...
    repository: Repository
    pull_request: PullRequestPayload
    installation: InstallationRef