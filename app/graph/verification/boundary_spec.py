"""
Boundary-spec check — the Critic's other deterministic, no-LLM verification
tool (alongside symbol_lookup.py's exact AST/symbol match).

Loads `ignition.boundaries.yaml` (repo root) and checks a PR's real
dependency graph against it. This is what lets Agent 1's gate reject a
layering inversion (e.g. a repository importing a route handler) as a hard
rule violation, and what lets the Critic tag an Agent 2A finding
`fact_checked` instead of merely `contextual`: an edge existing in the graph
only proves the import happened, not that it's a violation of anything —
matching it against a declared boundary rule is what proves the latter.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re

import yaml
from pydantic import BaseModel

from app.schemas.ast_payload import DependencyEdge

DEFAULT_SPEC_PATH = Path(__file__).resolve().parent.parent.parent.parent / "ignition.boundaries.yaml"


class BoundaryLayer(BaseModel):
    name: str
    patterns: list[str]


class BoundaryRule(BaseModel):
    from_layer: str
    to_layer: str
    disallowed: bool = True


class BoundarySpec(BaseModel):
    layers: list[BoundaryLayer] = []
    rules: list[BoundaryRule] = []


class BoundaryViolation(BaseModel):
    from_file: str
    to_file: str
    from_layer: str
    to_layer: str


def _glob_to_regex(pattern: str) -> re.Pattern:
    """
    Translates a `**`/`*` glob into a regex. Order matters: `**/` (any
    number of whole path segments, including zero) must be substituted
    before the bare `**` and `*` cases, since escaping the pattern first
    turns every literal `*`/`/` into `\\*`/`/` and those substitutions
    would otherwise clobber each other.
    """
    escaped = re.escape(pattern)
    escaped = escaped.replace(r"\*\*/", "(?:.*/)?")
    escaped = escaped.replace(r"\*\*", ".*")
    escaped = escaped.replace(r"\*", "[^/]*")
    return re.compile(f"^{escaped}$")


@lru_cache
def _compiled_layer_patterns(spec_json: str) -> tuple[tuple[str, tuple[re.Pattern, ...]], ...]:
    """Cache key is the spec's JSON so tests can load distinct specs without stale reuse."""
    spec = BoundarySpec.model_validate_json(spec_json)
    return tuple(
        (layer.name, tuple(_glob_to_regex(p) for p in layer.patterns))
        for layer in spec.layers
    )


def find_layer(spec: BoundarySpec, file_path: str) -> str | None:
    """Returns the first layer whose glob patterns match `file_path`, or None."""
    normalized = file_path.replace("\\", "/")
    for layer_name, patterns in _compiled_layer_patterns(spec.model_dump_json()):
        if any(p.match(normalized) for p in patterns):
            return layer_name
    return None


def is_boundary_violation(spec: BoundarySpec, from_file: str, to_file: str) -> BoundaryViolation | None:
    """
    Checks one edge against the spec. Returns the violation if `from_file`
    and `to_file` fall in layers with a disallowed rule between them, else
    None — an edge between two unmapped files, or two layers with no rule
    covering that direction, is not a violation (this spec only flags edges
    it knows about).
    """
    from_layer = find_layer(spec, from_file)
    to_layer = find_layer(spec, to_file)
    if from_layer is None or to_layer is None:
        return None

    for rule in spec.rules:
        if rule.disallowed and rule.from_layer == from_layer and rule.to_layer == to_layer:
            return BoundaryViolation(
                from_file=from_file, to_file=to_file, from_layer=from_layer, to_layer=to_layer,
            )
    return None


def check_boundary_violations(
    dependency_graph: list[DependencyEdge], spec: BoundarySpec
) -> list[BoundaryViolation]:
    """Checks every edge in the dependency graph against the spec, in order."""
    violations = []
    for edge in dependency_graph:
        violation = is_boundary_violation(spec, edge.from_file, edge.to_file)
        if violation is not None:
            violations.append(violation)
    return violations


@lru_cache
def load_default_boundary_spec() -> BoundarySpec:
    """
    Loads `ignition.boundaries.yaml` from the repo root. A missing file
    yields an empty spec (no layers, no rules) rather than an error — a
    deployment that hasn't configured boundaries yet shouldn't have every
    PR gate call fail.
    """
    if not DEFAULT_SPEC_PATH.exists():
        return BoundarySpec()
    raw = yaml.safe_load(DEFAULT_SPEC_PATH.read_text()) or {}
    return BoundarySpec(
        layers=[BoundaryLayer(**layer) for layer in raw.get("layers", [])],
        rules=[
            BoundaryRule(from_layer=rule["from"], to_layer=rule["to"], disallowed=rule.get("disallowed", True))
            for rule in raw.get("rules", [])
        ],
    )
