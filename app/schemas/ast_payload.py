"""
Contract for the JSON emitted by the Bun/ts-morph analyzer.

This is the schema most exposed to drift (Python model vs. TypeScript
emitter, no shared compiler). Per the PRD's open decision: generate one
side from the other (e.g. quicktype from this Pydantic model, or JSON
Schema validation in CI) rather than hand-syncing both directions.
"""
from pydantic import BaseModel


class SymbolRef(BaseModel):
    file_path: str
    symbol_name: str
    kind: str  # "function" | "class" | "interface" | "type" | "variable"
    line: int


class DependencyEdge(BaseModel):
    from_file: str
    to_file: str
    imported_symbols: list[str]


class PackageRef(BaseModel):
    name: str
    version: str
    # The declared spec at the base commit when this is a version bump;
    # None for a dependency the PR adds (audit P1-11: only new packages go
    # to Agent 2C's model). Mirrors PackageRef in ast-analyzer/analyzer.ts.
    previous_version: str | None = None


class ASTAnalyzerPayload(BaseModel):
    repo_full_name: str
    pr_number: int
    changed_files: list[str]
    symbols: list[SymbolRef]
    dependency_graph: list[DependencyEdge]
    hard_rule_violations: list[str] = []  # e.g. banned imports, blatant layer crossings
    changed_packages: list[PackageRef] = []  # NEW
    # The customer's ignition.boundaries.yaml at the PR's base commit (audit
    # P1-10), or None when the repo has none (or it's over 64 KB). Mirrors
    # ASTAnalyzerPayload.boundary_spec_yaml in ast-analyzer/analyzer.ts.
    boundary_spec_yaml: str | None = None
