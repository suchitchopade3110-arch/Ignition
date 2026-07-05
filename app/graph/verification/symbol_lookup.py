"""
Exact AST/symbol lookup — the Critic's hallucination-verification tool.

This is deliberately NOT vector similarity search. Per the PRD: "A
dedicated Critic agent re-checks every finding against the real codebase
using exact symbol/AST lookup, not vector similarity." Given how much
architectural weight rests on this distinction, it gets its own module
rather than being a private helper inside agent_3_critic.py.
"""
from app.schemas.ast_payload import ASTAnalyzerPayload, SymbolRef


class SymbolLookupError(Exception):
    """Raised when a finding references a symbol that doesn't exist in the AST graph."""


def verify_symbol_exists(ast_payload: ASTAnalyzerPayload, file_path: str, symbol_name: str) -> SymbolRef:
    """
    Exact-match lookup: does this symbol actually exist at this file path
    in the parsed AST graph? Raises if not — the caller (Critic) treats
    that as a hallucinated finding, not a soft warning.
    """
    for symbol in ast_payload.symbols:
        if symbol.file_path == file_path and symbol.symbol_name == symbol_name:
            return symbol

    raise SymbolLookupError(
        f"Symbol '{symbol_name}' not found in '{file_path}' — finding is unverified, "
        f"treat as a potential hallucination."
    )


def verify_dependency_edge_exists(ast_payload: ASTAnalyzerPayload, from_file: str, to_file: str) -> bool:
    """Confirms a claimed cross-file dependency actually exists in the dependency graph."""
    return any(
        edge.from_file == from_file and edge.to_file == to_file
        for edge in ast_payload.dependency_graph
    )