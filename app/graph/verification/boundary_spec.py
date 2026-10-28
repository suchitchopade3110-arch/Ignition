"""
Boundary-spec check — the Critic's other deterministic, no-LLM verification
tool (alongside symbol_lookup.py's exact AST/symbol match).

Parses the customer's `ignition.boundaries.yaml` (read by the analyzer from
their repo at the PR's base commit, audit P1-10) and checks a PR's real
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

# Ignition's own spec, kept as the template customers copy (audit P1-10).
# Reviews never use it: they use the spec from the reviewed repo.
DEFAULT_SPEC_PATH = Path(__file__).resolve().parent.parent.parent.parent / "docs" / "examples" / "ignition.boundaries.yaml"

MISSING_SPEC_NOTE = "No ignition.boundaries.yaml found; boundary checks skipped"
INVALID_SPEC_NOTE = "ignition.boundaries.yaml could not be parsed; boundary checks skipped"


class BoundarySpecError(ValueError):
    """The spec file exists but isn't a valid spec."""


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


def load_boundary_spec(yaml_text: str | None) -> BoundarySpec:
    """
    Parses a spec with yaml.safe_load (no tags, no code). None or an empty
    document is an empty spec (no layers, no rules: nothing is flagged).
    Anything that isn't a valid spec raises BoundarySpecError.
    """
    if yaml_text is None:
        return BoundarySpec()
    try:
        raw = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        raise BoundarySpecError(f"not valid YAML: {exc}") from exc
    if raw is None:
        return BoundarySpec()
    if not isinstance(raw, dict):
        raise BoundarySpecError("the document must be a mapping with `layers` and `rules`")
    try:
        return BoundarySpec(
            layers=[BoundaryLayer(**layer) for layer in raw.get("layers") or []],
            rules=[
                BoundaryRule(from_layer=rule["from"], to_layer=rule["to"], disallowed=rule.get("disallowed", True))
                for rule in raw.get("rules") or []
            ],
        )
    except (KeyError, TypeError, ValueError) as exc:  # pydantic's ValidationError is a ValueError
        raise BoundarySpecError(f"invalid layer or rule: {exc}") from exc


def spec_from_payload(yaml_text: str | None) -> tuple[BoundarySpec, str | None]:
    """The review's spec plus the one-line note the comment shows when there
    isn't a usable one (audit P1-10)."""
    if yaml_text is None:
        return BoundarySpec(), MISSING_SPEC_NOTE
    try:
        return load_boundary_spec(yaml_text), None
    except BoundarySpecError:
        return BoundarySpec(), INVALID_SPEC_NOTE


@lru_cache
def load_default_boundary_spec() -> BoundarySpec:
    """Ignition's own spec (docs/examples/ignition.boundaries.yaml), the
    template customers copy. Not used to review anything."""
    if not DEFAULT_SPEC_PATH.exists():
        return BoundarySpec()
    return load_boundary_spec(DEFAULT_SPEC_PATH.read_text())
