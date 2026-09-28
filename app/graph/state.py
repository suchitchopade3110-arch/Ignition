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

# "fact_checked": the finding's claim was checked against a hard rule (right
# now: a boundary-spec layer violation, app/graph/verification/boundary_spec.py)
# and proven to actually violate it — not merely proven to reference
# something real. "contextual": the finding survived hallucination
# verification (its symbol/edge exists, or it made no checkable AST claim by
# design) but its "this is a problem" judgment is still the LLM's, unproven
# against any hard rule. Set by agent_3_critic._verify_findings; see that
# module's docstring for exactly which findings land in which tier.
VerificationTier = Literal["fact_checked", "contextual"]


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
    # Defaults to the weaker tier — only agent_3_critic._verify_findings is
    # allowed to upgrade a finding to "fact_checked", and only after proving
    # it against the boundary spec.
    verification_tier: VerificationTier = "contextual"


class ClearAgentFindings(list):
    """
    Sentinel subclass of list, tagged with the agent whose prior findings
    should be dropped from the accumulated `findings` list on merge —
    every other agent's findings pass through untouched. Used on the
    narrow hallucination-retry edge (Critic -> Agent 2A only, see
    routing.py/workflow.py): only Agent 2A gets re-run on retry, so only
    its own (partly hallucinated) findings from the failed pass need to
    go. 2B/2C aren't re-run that pass, so their already-verified findings
    must survive instead of being wiped wholesale, which a plain
    replace-the-whole-list reset would otherwise do.
    """

    def __init__(self, agent: str):
        super().__init__()
        self.agent = agent


def merge_findings(left: list[Finding], right: list[Finding]) -> list[Finding]:
    if isinstance(right, ClearAgentFindings):
        return [f for f in left if f.agent != right.agent]
    return left + right


class RejectedClaim(BaseModel):
    """
    A symbol_ref/dependency_edge_ref claim that failed hallucination
    verification on a prior Critic pass. Threaded back into the retry
    re-prompt (agent_2a_structural.md via agent_2a_struct.py) so a retried
    pass knows exactly which refs already didn't check out, instead of
    blindly re-guessing (and likely re-failing) the same ones.
    """
    symbol_ref: str | None = None
    dependency_edge_ref: tuple[str, str] | None = None
    description: str


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

    # Bounded retry loop control (Agent 3 -> Agent 2A)
    hallucination_retry_count: Annotated[int, operator.add] = 0

    # Refs the Critic rejected as hallucinated on a prior pass, accumulated
    # across retries (not reset) so a later attempt still knows what
    # failed on an earlier one too. Read by agent_2a_struct on retry so its
    # re-prompt can steer away from repeating them.
    rejected_claims: Annotated[list[RejectedClaim], operator.add] = Field(default_factory=list)

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