"""
Agent 2C — Security & Supply Chain Auditor (Sub-Graph C). Hybrid:
deterministic registry checks + lightweight semantic scoring.

Phase 1:   deterministic OSV vulnerability lookup (no LLM)
Phase 1.5: deterministic npm publish-recency lookup (no LLM)
Phase 2:   semantic slopsquat/typosquat heuristics (LLM), grounded in the
           real publish-recency data fetched in phase 1.5 rather than
           asked to guess metadata it was never given
"""
import logging
from datetime import datetime, timezone
from pathlib import Path
import httpx

from app.config import get_settings
from app.graph.state import ReviewState, Finding
from app.services.llm_client import get_llm_client
from app.services.finding_parser import parse_findings_json

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "agent_2c_security.md"

OSV_API_URL = "https://api.osv.dev/v1/query"
NPM_REGISTRY_URL = "https://registry.npmjs.org"


async def _phase1_deterministic_registry_check(
    client: httpx.AsyncClient, package_name: str, version: str
) -> list[Finding]:
    """Pure deterministic OSV lookup — no LLM, cheap, runs first."""
    findings: list[Finding] = []
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


async def _fetch_publish_age_days(
    client: httpx.AsyncClient, package_name: str, version: str
) -> float | None:
    """
    Real npm registry lookup for how long ago this exact version was
    published. Returns None (not zero) when the registry doesn't have an
    answer — a missing package/version means "unknown", not "just
    published"; those must never be treated the same by the caller.
    """
    try:
        response = await client.get(f"{NPM_REGISTRY_URL}/{package_name}")
        if response.status_code != 200:
            return None
        published_at = response.json().get("time", {}).get(version)
        if not published_at:
            return None
        published_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        age = datetime.now(timezone.utc) - published_dt
        return age.total_seconds() / 86400
    except Exception:
        logger.exception("Failed to fetch npm publish date for %s@%s", package_name, version)
        return None


async def _phase2_semantic_slopsquat_check(
    package_name: str, publish_age_days: float | None
) -> list[Finding]:
    """
    Semantic heuristics for slopsquatted/typosquatted packages, grounded in
    the real publish-age data fetched above (rather than asked to invent
    recency/maintainer/download signals it was never given).
    """
    prompt_template = PROMPT_PATH.read_text()
    llm = get_llm_client()
    publish_age_str = (
        f"{publish_age_days:.1f} days ago" if publish_age_days is not None else "unknown (registry lookup failed)"
    )
    prompt = prompt_template.format(package_name=package_name, publish_age=publish_age_str)

    try:
        raw_response = await llm.complete(prompt, agent_name="agent_2c_security")
        return parse_findings_json(raw_response, agent_name="agent_2c_security")
    except Exception:
        logger.exception("agent_2c_security phase-2 LLM call failed for %s; skipping", package_name)
        return []


async def agent_2c_security(state: ReviewState) -> dict:
    findings: list[Finding] = []
    settings = get_settings()

    # Dedupe (name, version) pairs — a lockfile bump can list the same
    # exact pin more than once across workspaces; there's no reason to
    # hit OSV/npm/the LLM twice for an identical package@version.
    changed_packages = list({
        (pkg.name, pkg.version) for pkg in state.ast_payload.changed_packages
    })

    async with httpx.AsyncClient() as client:
        for name, version in changed_packages:
            findings += await _phase1_deterministic_registry_check(client, name, version)

            publish_age_days = await _fetch_publish_age_days(client, name, version)
            if publish_age_days is not None and publish_age_days < settings.slopsquat_fresh_package_days:
                findings.append(
                    Finding(
                        agent="agent_2c_security",
                        file_path="package.json",
                        description=(
                            f"{name}@{version} was published to npm {publish_age_days:.1f} days ago "
                            f"(threshold: {settings.slopsquat_fresh_package_days}d) — freshly-published "
                            f"dependencies are a common slopsquat/supply-chain vector"
                        ),
                        severity="medium",
                    )
                )

            findings += await _phase2_semantic_slopsquat_check(name, publish_age_days)

    return {"findings": findings}