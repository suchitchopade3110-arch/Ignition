from app.graph.verification.symbol_lookup import (
    verify_symbol_exists,
    verify_dependency_edge_exists,
    verify_dependency_edge_or_raise,
    SymbolLookupError,
    DependencyEdgeLookupError,
)
from app.schemas.ast_payload import ASTAnalyzerPayload, DependencyEdge, SymbolRef

import pytest


def _ast_payload(symbols=None, dependency_graph=None) -> ASTAnalyzerPayload:
    return ASTAnalyzerPayload(
        repo_full_name="acme/widgets", pr_number=1, changed_files=[],
        symbols=symbols or [], dependency_graph=dependency_graph or [],
    )


def test_verify_symbol_exists_finds_matching_symbol():
    ast_payload = _ast_payload(symbols=[SymbolRef(file_path="a.ts", symbol_name="foo", kind="function", line=1)])
    result = verify_symbol_exists(ast_payload, "a.ts", "foo")
    assert result.symbol_name == "foo"


def test_verify_symbol_exists_raises_when_file_matches_but_name_does_not():
    ast_payload = _ast_payload(symbols=[SymbolRef(file_path="a.ts", symbol_name="foo", kind="function", line=1)])
    with pytest.raises(SymbolLookupError):
        verify_symbol_exists(ast_payload, "a.ts", "bar")


def test_verify_symbol_exists_raises_when_name_matches_but_file_does_not():
    ast_payload = _ast_payload(symbols=[SymbolRef(file_path="a.ts", symbol_name="foo", kind="function", line=1)])
    with pytest.raises(SymbolLookupError):
        verify_symbol_exists(ast_payload, "b.ts", "foo")


def test_verify_dependency_edge_exists_true_for_real_edge():
    ast_payload = _ast_payload(dependency_graph=[DependencyEdge(from_file="a", to_file="b", imported_symbols=[])])
    assert verify_dependency_edge_exists(ast_payload, "a", "b") is True


def test_verify_dependency_edge_exists_false_for_missing_edge():
    ast_payload = _ast_payload(dependency_graph=[])
    assert verify_dependency_edge_exists(ast_payload, "a", "b") is False


def test_verify_dependency_edge_or_raise_raises_for_missing_edge():
    ast_payload = _ast_payload(dependency_graph=[])
    with pytest.raises(DependencyEdgeLookupError):
        verify_dependency_edge_or_raise(ast_payload, "a", "b")


def test_verify_dependency_edge_or_raise_passes_for_real_edge():
    ast_payload = _ast_payload(dependency_graph=[DependencyEdge(from_file="a", to_file="b", imported_symbols=[])])
    verify_dependency_edge_or_raise(ast_payload, "a", "b")  # must not raise
