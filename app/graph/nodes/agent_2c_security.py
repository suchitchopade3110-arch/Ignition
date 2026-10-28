"""
Agent 2C — Security & Supply Chain Auditor (Sub-Graph C). Hybrid:
deterministic registry checks + lightweight semantic scoring.

Phase 1:   deterministic OSV vulnerability lookup (no LLM)
Phase 1.5: deterministic npm publish-recency lookup (no LLM)
Phase 2:   semantic slopsquat/typosquat heuristics (LLM), grounded in the
           real publish-recency data fetched in phase 1.5 rather than
           asked to guess metadata it was never given

Bounded (audit P1-11): phases 1 and 1.5 run for every changed package, but
all OSV and npm calls share one asyncio.Semaphore(4). Phase 2 is ONE
batched prompt, and only for packages that are new in this PR (not just a
version bump) AND either published under 7 days ago or within edit
distance 2 of a popular npm name (app/data/popular_npm_packages.txt,
refreshed by scripts/refresh_popular_npm.py). Without that list every new
package goes to the model: fail toward checking, never toward skipping.
A 50-package lockfile bump makes at most one LLM call.
"""
import asyncio
import logging
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
import httpx

from app.config import get_settings
from app.graph.state import ReviewState, Finding
from app.schemas.ast_payload import PackageRef
from app.services.llm_client import get_llm_client
from app.services.prompt_safety import fence, new_nonce, untrusted_notice
from app.services.finding_parser import parse_findings_json

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "agent_2c_security.md"

# One-per-line npm names (comments with #); the typosquat prefilter's list.
POPULAR_PACKAGES_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "popular_npm_packages.txt"
# Concurrent OSV + npm registry calls per review (audit P1-11).
REGISTRY_CONCURRENCY = 4
TYPOSQUAT_MAX_DISTANCE = 2

OSV_API_URL = "https://api.osv.dev/v1/query"
NPM_REGISTRY_URL = "https://registry.npmjs.org"

# Process-local, unbounded for the lifetime of the process — a given
# package@version's npm publish date is an immutable historical fact, so
# unlike a vuln-database result it never goes stale and is always safe to
# reuse across reviews/repos. Caches the raw publish TIMESTAMP, not a
# computed age-in-days, so a cache hit is re-diffed against "now" each
# time rather than freezing the age at whatever it was on the first
# lookup. Only successful lookups are cached (see _fetch_publish_age_days)
# so a transient registry failure doesn't get permanently remembered as
# "unknown".
_publish_age_cache: dict[tuple[str, str], datetime] = {}


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
                severity_floor="high",  # an OSV hit is proven, not judged (audit P1-3)
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

    Cached by (package_name, version) — see _publish_age_cache's docstring
    for why that's safe. The cached value is a fixed publish timestamp
    re-diffed against "now" on every hit, so a cache hit from an hour ago
    doesn't silently under-report the age.
    """
    cache_key = (package_name, version)
    cached_published_at = _publish_age_cache.get(cache_key)
    if cached_published_at is not None:
        return (datetime.now(timezone.utc) - cached_published_at).total_seconds() / 86400

    try:
        response = await client.get(f"{NPM_REGISTRY_URL}/{package_name}")
        if response.status_code != 200:
            return None
        published_at = response.json().get("time", {}).get(version)
        if not published_at:
            return None
        published_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        _publish_age_cache[cache_key] = published_dt
        return (datetime.now(timezone.utc) - published_dt).total_seconds() / 86400
    except Exception:
        logger.exception("Failed to fetch npm publish date for %s@%s", package_name, version)
        return None


class Phase2Failed(Exception):
    pass


async def _phase2_semantic_slopsquat_check(packages: list[tuple[str, float | None]]) -> list[Finding]:
    """
    Semantic heuristics for slopsquatted/typosquatted packages, grounded in
    the real publish-age data fetched above (rather than asked to invent
    recency/maintainer/download signals it was never given). ONE prompt for
    every package that passed the prefilter (audit P1-11).
    """
    prompt_template = PROMPT_PATH.read_text()
    llm = get_llm_client()
    lines = [
        f"- {name} — published "
        + (f"{age:.1f} days ago" if age is not None else "unknown (registry lookup failed)")
        for name, age in packages
    ]
    nonce = new_nonce()
    prompt = prompt_template.format(
        packages=fence("packages", "\n".join(lines), nonce),
        untrusted_notice=untrusted_notice(nonce),
    )

    try:
        raw_response = await llm.complete(prompt, agent_name="agent_2c_security")
        return parse_findings_json(raw_response, agent_name="agent_2c_security")
    except Exception as exc:
        logger.exception("agent_2c_security phase-2 LLM call failed for %d packages", len(packages))
        raise Phase2Failed([name for name, _ in packages]) from exc


@lru_cache
def load_popular_packages() -> frozenset[str] | None:
    """The popular-npm list, or None when the data file is missing (then
    every new package goes to the model)."""
    try:
        text = POPULAR_PACKAGES_PATH.read_text()
    except FileNotFoundError:
        logger.warning("Popular npm list missing (%s); every new package goes to the LLM", POPULAR_PACKAGES_PATH)
        return None
    names = {line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")}
    return frozenset(names)


def _within_distance(a: str, b: str, limit: int) -> bool:
    """Levenshtein distance(a, b) <= limit. Banded: only cells within
    `limit` of the diagonal can stay under the limit, so each row costs
    O(limit) instead of O(len(b))."""
    if abs(len(a) - len(b)) > limit:
        return False
    big = limit + 1
    previous = {j: j for j in range(0, min(len(b), limit) + 1)}
    for i in range(1, len(a) + 1):
        current: dict[int, int] = {}
        for j in range(max(0, i - limit), min(len(b), i + limit) + 1):
            if j == 0:
                current[j] = i
                continue
            current[j] = min(
                previous.get(j, big) + 1,
                current.get(j - 1, big) + 1,
                previous.get(j - 1, big) + (a[i - 1] != b[j - 1]),
            )
        if min(current.values()) > limit:
            return False
        previous = current
    return previous.get(len(b), big) <= limit


@lru_cache(maxsize=4)
def _names_by_length(popular: frozenset[str]) -> dict[int, tuple[str, ...]]:
    by_length: dict[int, list[str]] = {}
    for name in popular:
        by_length.setdefault(len(name), []).append(name)
    return {length: tuple(names) for length, names in by_length.items()}


def _near_popular_name(name: str, popular: frozenset[str]) -> bool:
    by_length = _names_by_length(popular)
    return any(
        _within_distance(name, other, TYPOSQUAT_MAX_DISTANCE)
        for length in range(len(name) - TYPOSQUAT_MAX_DISTANCE, len(name) + TYPOSQUAT_MAX_DISTANCE + 1)
        for other in by_length.get(length, ())
    )


def needs_llm_review(pkg: PackageRef, publish_age_days: float | None, popular: frozenset[str] | None,
                     fresh_days: int) -> bool:
    """The phase-2 prefilter (audit P1-11)."""
    if pkg.previous_version is not None:
        return False  # a version bump of a dependency the repo already had
    if popular is None:
        return True  # no list to compare against: check rather than skip
    if publish_age_days is not None and publish_age_days < fresh_days:
        return True
    if pkg.name in popular:
        return False
    return _near_popular_name(pkg.name, popular)


async def _process_package(
    client: httpx.AsyncClient, settings, name: str, version: str, limit: asyncio.Semaphore | None = None,
) -> tuple[list[Finding], float | None]:
    """
    Phases 1 and 1.5 for one package@version — the deterministic part.
    Returns (findings, publish_age_days); the caller decides from the age
    whether the package also goes to the batched phase 2. Every OSV and npm
    call holds the shared semaphore (audit P1-11).
    """
    limit = limit or asyncio.Semaphore(REGISTRY_CONCURRENCY)
    async with limit:
        findings = await _phase1_deterministic_registry_check(client, name, version)
    async with limit:
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
                severity_floor="medium",  # registry fact, not model judgment (audit P1-3)
            )
        )
    return findings, publish_age_days


async def agent_2c_security(state: ReviewState) -> dict:
    settings = get_settings()

    # Dedupe (name, version) pairs — a lockfile bump can list the same
    # exact pin more than once across workspaces; there's no reason to
    # hit OSV/npm twice for an identical package@version.
    packages: dict[tuple[str, str], PackageRef] = {}
    for pkg in state.ast_payload.changed_packages:
        packages.setdefault((pkg.name, pkg.version), pkg)

    limit = asyncio.Semaphore(REGISTRY_CONCURRENCY)
    async with httpx.AsyncClient() as client:
        per_package = await asyncio.gather(*(
            _process_package(client, settings, name, version, limit) for name, version in packages
        ))

    findings = [f for package_findings, _ in per_package for f in package_findings]
    def prefilter() -> list[tuple[str, float | None]]:
        popular = load_popular_packages()
        return [
            (pkg.name, age)
            for pkg, (_, age) in zip(packages.values(), per_package)
            if needs_llm_review(pkg, age, popular, settings.slopsquat_fresh_package_days)
        ]

    # CPU work over a 5,000-name list: off the event loop (audit P1-7).
    candidates = await asyncio.to_thread(prefilter)

    result: dict = {"findings": findings}
    if candidates:
        try:
            result["findings"] = findings + await _phase2_semantic_slopsquat_check(candidates)
        except Phase2Failed:
            # Keep the deterministic phase-1/1.5 findings; report the gap.
            result["agent_errors"] = ["agent_2c_security"]
    return result
