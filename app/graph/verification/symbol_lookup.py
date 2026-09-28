"""
Exact AST/symbol lookup — the Critic's hallucination-verification tool.

This is deliberately NOT vector similarity search. Per the PRD: "A
dedicated Critic agent re-checks every finding against the real codebase
using exact symbol/AST lookup, not vector similarity." Given how much
architectural weight rests on this distinction, it gets its own module
rather than being a private helper inside agent_3_critic.py.
"""
import logging

from app.schemas.ast_payload import ASTAnalyzerPayload, SymbolRef

logger = logging.getLogger(__name__)


class SymbolLookupError(Exception):
    """Raised when a finding references a symbol that doesn't exist in the AST graph."""


class DependencyEdgeLookupError(Exception):
    """Raised when a finding references a cross-file import that doesn't exist in the dependency graph."""


def _normalize_path(path: str) -> str:
    """
    Collapses path spellings the ts-morph analyzer and an LLM finding can
    legitimately disagree on for the same real file: backslash vs forward
    slash, a leading './', a trailing slash, and the file extension (a
    dynamic `import('./foo')` resolves differently than the declaration
    site's './foo.ts').
    """
    normalized = path.replace("\\", "/").strip()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    for ext in (".tsx", ".ts", ".jsx", ".js"):
        if normalized.endswith(ext):
            normalized = normalized[: -len(ext)]
            break
    return normalized.rstrip("/")


def _is_barrel_path(normalized_path: str) -> bool:
    return normalized_path.rsplit("/", 1)[-1] == "index"


def _find_near_miss_symbol(ast_payload: ASTAnalyzerPayload, file_path: str, symbol_name: str) -> SymbolRef | None:
    """
    Best-effort recovery for known ts-morph blind spots — dynamic imports,
    barrel re-exports, and DI-container registration all produce symbols
    that are real but don't land at the exact (file_path, symbol_name)
    pair a finding names:
      1. Same declaration, different path SPELLING (extension, './'
         prefix, separator).
      2. The claimed path is a barrel (index.ts/tsx/js) and the symbol is
         actually declared in a sibling/descendant file re-exported
         through it.
    Returns the matching SymbolRef, or None if nothing recovers it — a
    genuine miss, not a graph gap.
    """
    normalized_target = _normalize_path(file_path)

    for symbol in ast_payload.symbols:
        if symbol.symbol_name == symbol_name and _normalize_path(symbol.file_path) == normalized_target:
            return symbol

    if _is_barrel_path(normalized_target):
        barrel_dir = normalized_target.rsplit("/", 1)[0] if "/" in normalized_target else ""
        if barrel_dir:  # a bare top-level "index" is too broad to scope a match to
            for symbol in ast_payload.symbols:
                if symbol.symbol_name == symbol_name and _normalize_path(symbol.file_path).startswith(f"{barrel_dir}/"):
                    return symbol

    return None


def _find_near_miss_edge(ast_payload: ASTAnalyzerPayload, from_file: str, to_file: str) -> bool:
    """
    Barrel-resolution fallback for dependency edges: the AST graph often
    records an import as `from_file -> some/index.ts` rather than the file
    that actually declares the imported symbol behind that barrel. If a
    two-hop path through an index/barrel file connects the claimed
    endpoints, treat it as a graph gap, not a hallucinated edge.
    """
    normalized_from = _normalize_path(from_file)
    normalized_to = _normalize_path(to_file)

    if any(
        _normalize_path(edge.from_file) == normalized_from and _normalize_path(edge.to_file) == normalized_to
        for edge in ast_payload.dependency_graph
    ):
        return True

    barrel_hops = {
        _normalize_path(edge.to_file)
        for edge in ast_payload.dependency_graph
        if _normalize_path(edge.from_file) == normalized_from and _is_barrel_path(_normalize_path(edge.to_file))
    }
    return any(
        _normalize_path(edge.from_file) in barrel_hops and _normalize_path(edge.to_file) == normalized_to
        for edge in ast_payload.dependency_graph
    )


def verify_symbol_exists(ast_payload: ASTAnalyzerPayload, file_path: str, symbol_name: str) -> SymbolRef:
    """
    Exact-match lookup: does this symbol actually exist at this file path
    in the parsed AST graph? Raises if not, UNLESS a normalized/near-match
    fallback recovers it (see _find_near_miss_symbol) — that's logged
    separately as a "near_miss_graph_gap" (a real symbol the static graph
    missed) rather than being dropped as a hallucination.
    """
    for symbol in ast_payload.symbols:
        if symbol.file_path == file_path and symbol.symbol_name == symbol_name:
            return symbol

    near_miss = _find_near_miss_symbol(ast_payload, file_path, symbol_name)
    if near_miss is not None:
        logger.warning(
            "near_miss_graph_gap: symbol '%s' claimed at '%s' matched '%s' only via path "
            "normalization or barrel resolution — likely a dynamic-import/barrel-export/"
            "DI-container blind spot in the AST graph, not a hallucination.",
            symbol_name, file_path, near_miss.file_path,
        )
        return near_miss

    raise SymbolLookupError(
        f"Symbol '{symbol_name}' not found in '{file_path}' — finding is unverified, "
        f"treat as a potential hallucination."
    )


def verify_dependency_edge_exists(ast_payload: ASTAnalyzerPayload, from_file: str, to_file: str) -> bool:
    """
    Confirms a claimed cross-file dependency actually exists in the
    dependency graph — exactly, or, failing that, via the same
    normalized/barrel-hop near-match fallback as verify_symbol_exists,
    logged as a "near_miss_graph_gap" rather than treated as an outright
    miss.
    """
    if any(edge.from_file == from_file and edge.to_file == to_file for edge in ast_payload.dependency_graph):
        return True

    if _find_near_miss_edge(ast_payload, from_file, to_file):
        logger.warning(
            "near_miss_graph_gap: dependency edge '%s' -> '%s' resolved only via path "
            "normalization or a barrel re-export hop — likely a ts-morph graph gap, not "
            "a hallucinated edge.",
            from_file, to_file,
        )
        return True

    return False


def verify_dependency_edge_or_raise(ast_payload: ASTAnalyzerPayload, from_file: str, to_file: str) -> None:
    """
    Same check as verify_dependency_edge_exists, but raises — the shape
    the Critic's verification loop wants (matching verify_symbol_exists),
    since it treats "not found" as a hallucination signal, not a bool to
    branch on inline.
    """
    if not verify_dependency_edge_exists(ast_payload, from_file, to_file):
        raise DependencyEdgeLookupError(
            f"Dependency edge '{from_file}' -> '{to_file}' not found in the dependency "
            f"graph — finding is unverified, treat as a potential hallucination."
        )