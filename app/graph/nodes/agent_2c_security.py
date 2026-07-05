"""
Agent 2C — Security & Supply Chain Auditor (Sub-Graph C). Hybrid:
deterministic registry checks + lightweight semantic scoring.

Phase 1: deterministic OSV/registry API lookups (no LLM)
Phase 2: semantic slopsquat/typosquat heuristics (LLM)
"""
import logging
from pathlib import Path
import httpx

from app.graph.state import ReviewState, Finding
from app.services.llm_client import LLMClient
from app.services.finding_parser import parse_findings_json

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "agent_2c_security.md"

OSV_API_URL = "https://api.osv.dev/v1/query"


async def _phase1_deterministic_registry_check(package_name: str, version: str) -> list[Finding]:
    """Pure deterministic OSV/registry lookups — no LLM, cheap, runs first."""
    findings: list[Finding] = []
    async with httpx.AsyncClient() as client:
        response = await client.post(
            OSV_API_URL, json={"package": {"name": package_name}, "version": version}
        )
        if response.status_code == 200 and response.json().get("vulns"):
            findings.append(
                Finding(
                    agent="agent_2c_security",
                    file_path="package.json",
                    description=f"Known vulnerability in {package_name}@{version}",
                    severity="high",
                )
            )
    return findings


async def _phase2_semantic_slopsquat_check(package_name: str) -> list[Finding]:
    """Semantic heuristics for freshly-published / slopsquatted packages."""
    prompt_template = PROMPT_PATH.read_text()
    llm = LLMClient()
    prompt = prompt_template.format(package_name=package_name)

    try:
        raw_response = await llm.complete(prompt)
        return parse_findings_json(raw_response, agent_name="agent_2c_security")
    except Exception:
        logger.exception("agent_2c_security phase-2 LLM call failed for %s; skipping", package_name)
        return []


async def agent_2c_security(state: ReviewState) -> dict:
    findings: list[Finding] = []

    # Package extraction from the diff would come from the AST payload's
    # dependency graph in a real implementation.
    changed_packages: list[tuple[str, str]] = []  # [(name, version), ...] — TODO: derive from state

    for name, version in changed_packages:
        findings += await _phase1_deterministic_registry_check(name, version)
        findings += await _phase2_semantic_slopsquat_check(name)

    return {"findings": findings}