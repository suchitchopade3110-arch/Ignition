"""
Agent 1 — Context Fetcher / Hard-Rule Gate. Pure deterministic code, no LLM.

Builds on the AST payload already present in state (produced by the Bun
service before the graph started) and checks for blatant, rule-based
violations that don't need semantic judgment: banned imports, layer
crossings, etc.
"""
from app.graph.state import ReviewState

BANNED_IMPORT_PATTERNS = ["eval(", "child_process.exec("]


def agent_1_gate(state: ReviewState) -> dict:
    violations = list(state.ast_payload.hard_rule_violations)

    if violations:
        return {
            "hard_rule_violation": True,
            "rejection_reason": "; ".join(violations),
        }

    return {"hard_rule_violation": False}