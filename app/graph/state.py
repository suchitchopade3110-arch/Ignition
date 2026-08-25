"""
LangGraph state definition.

Sub-Graphs A, B, C write findings in parallel — each field they touch needs
an explicit reducer (Annotated + operator) or LangGraph will throw on
concurrent writes to the same key. This is the PRD's most-flagged pitfall,
so it's made explicit here rather than left implicit.
"""
from __future__ import annotations
from typing import Annotated, Literal
import operator

from pydantic import BaseModel, Field

from app.schemas.ast_payload import ASTAnalyzerPayload
from app.schemas.github import PullRequestWebhook

Severity = Literal["none", "low", "medium", "high", "critical"]


class Finding(BaseModel):
    agent: str
    file_path: str
    line: int | None = None
    description: str
    severity: Severity
    suggested_patch: str | None = None
    # Exact-lookup verification hooks (app/graph/verification/symbol_lookup.py).
    # An agent that flags an issue tied to a specific declared symbol or a
    # specific cross-file import should populate one of these so the Critic
    # can confirm the claim against the real AST graph before trusting it.
    # Neither is required — a security/dependency finding (Agent 2C) has no
    # AST symbol to point at, and is passed through unverified by design.
    symbol_ref: str | None = None
    dependency_edge_ref: tuple[str, str] | None = None  # (from_file, to_file)


class ResetFindings(list):
    """
    Sentinel subclass of list. When a node returns this as the `findings`
    update, merge_findings replaces the accumulated list instead of
    appending to it — used on the hallucination-retry edge (Critic ->
    Agent 1) so a second pass's findings don't pile up on top of the first
    pass's, which the additive reducer would otherwise do silently.
    """


def merge_findings(left: list[Finding], right: list[Finding]) -> list[Finding]:
    if isinstance(right, ResetFindings):
        return list(right)
    return left + right


class ReviewState(BaseModel):
    # Immutable input context
    repo_full_name: str
    pr_number: int
    installation_id: int
    diff_text: str = ""
    ast_payload: ASTAnalyzerPayload

    # Written once by Agent 1
    hard_rule_violation: bool = False
    rejection_reason: str | None = None

    # Written in parallel by Sub-Graphs A/B/C — reducer required
    findings: Annotated[list[Finding], merge_findings] = Field(default_factory=list)

    # Written by the Critic
    verified_findings: list[Finding] = Field(default_factory=list)
    acs_score: float | None = None
    is_regression: bool = False
    hitl_severity: Severity = "none"

    # Explicit retry signal — overwritten each Critic pass, never
    # accumulated. Kept separate from acs_score so "no score yet" and
    # "score is genuinely null" can never be confused (routing.py used to
    # overload acs_score is None for this, which was a placeholder hack).
    critic_wants_retry: bool = False

    # Bounded retry loop control (Agent 3 -> Agent 1)
    hallucination_retry_count: Annotated[int, operator.add] = 0

    # Terminal
    final_comment_markdown: str | None = None

    # Set by agent_4_autofix — informational, not used in routing decisions
    autofix_posted: int = 0
    autofix_failed: int = 0

    @classmethod
    def from_ast_payload(cls, ast_payload: ASTAnalyzerPayload, event: PullRequestWebhook) -> "ReviewState":
        return cls(
            repo_full_name=event.repository.full_name,
            pr_number=event.pull_request.number,
            installation_id=event.installation.id,
            ast_payload=ast_payload,
        )