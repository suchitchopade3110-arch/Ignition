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


def merge_findings(left: list[Finding], right: list[Finding]) -> list[Finding]:
    return left + right


class ReviewState(BaseModel):
    # Immutable input context
    repo_full_name: str
    pr_number: int
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

    # Bounded retry loop control (Agent 3 -> Agent 1)
    hallucination_retry_count: Annotated[int, operator.add] = 0

    # Terminal
    final_comment_markdown: str | None = None

    @classmethod
    def from_ast_payload(cls, ast_payload: ASTAnalyzerPayload, event: PullRequestWebhook) -> "ReviewState":
        return cls(
            repo_full_name=event.repository.full_name,
            pr_number=event.pull_request.number,
            ast_payload=ast_payload,
        )