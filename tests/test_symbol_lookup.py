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


class TestNearMissGraphGap:
    """
    ts-morph's static AST graph has known blind spots — dynamic imports,
    barrel re-exports, DI-container registration — where a real symbol/edge
    doesn't land at the exact spelling a finding names. These must be
    rescued (not dropped as hallucinations) and logged distinctly so the
    gap itself stays visible.
    """

    def test_symbol_near_miss_on_path_spelling_is_recovered_and_logged(self, caplog):
        # Real declaration lives at "a.ts"; the finding names it without
        # the extension, as a dynamic import site might.
        ast_payload = _ast_payload(symbols=[SymbolRef(file_path="a.ts", symbol_name="foo", kind="function", line=1)])
        with caplog.at_level("WARNING"):
            result = verify_symbol_exists(ast_payload, "a", "foo")
        assert result.symbol_name == "foo"
        assert "near_miss_graph_gap" in caplog.text

    def test_symbol_near_miss_via_barrel_index_is_recovered_and_logged(self, caplog):
        # Symbol is actually declared in a sibling file under the same
        # directory as the claimed barrel (index) path.
        ast_payload = _ast_payload(
            symbols=[SymbolRef(file_path="src/services/UserService.ts", symbol_name="UserService", kind="class", line=1)]
        )
        with caplog.at_level("WARNING"):
            result = verify_symbol_exists(ast_payload, "src/services/index.ts", "UserService")
        assert result.file_path == "src/services/UserService.ts"
        assert "near_miss_graph_gap" in caplog.text

    def test_symbol_with_no_near_miss_still_raises_as_a_clean_hallucination(self, caplog):
        ast_payload = _ast_payload(symbols=[SymbolRef(file_path="a.ts", symbol_name="foo", kind="function", line=1)])
        with caplog.at_level("WARNING"):
            with pytest.raises(SymbolLookupError):
                verify_symbol_exists(ast_payload, "b.ts", "madeUpFn")
        assert "near_miss_graph_gap" not in caplog.text

    def test_top_level_barrel_is_too_broad_to_near_miss(self):
        # A bare top-level "index" (no directory to scope the match to)
        # must not turn into "match this symbol name anywhere in the repo".
        ast_payload = _ast_payload(
            symbols=[SymbolRef(file_path="unrelated/deep/path/Thing.ts", symbol_name="foo", kind="function", line=1)]
        )
        with pytest.raises(SymbolLookupError):
            verify_symbol_exists(ast_payload, "index.ts", "foo")

    def test_dependency_edge_near_miss_on_path_spelling_is_recovered_and_logged(self, caplog):
        ast_payload = _ast_payload(
            dependency_graph=[DependencyEdge(from_file="a.ts", to_file="b.ts", imported_symbols=[])]
        )
        with caplog.at_level("WARNING"):
            assert verify_dependency_edge_exists(ast_payload, "a", "b") is True
        assert "near_miss_graph_gap" in caplog.text

    def test_dependency_edge_near_miss_via_barrel_hop_is_recovered_and_logged(self, caplog):
        # api.ts -> services/index.ts -> services/db.ts: a claimed direct
        # edge from api.ts to db.ts is really a two-hop barrel re-export.
        ast_payload = _ast_payload(
            dependency_graph=[
                DependencyEdge(from_file="api.ts", to_file="services/index.ts", imported_symbols=[]),
                DependencyEdge(from_file="services/index.ts", to_file="services/db.ts", imported_symbols=[]),
            ]
        )
        with caplog.at_level("WARNING"):
            assert verify_dependency_edge_exists(ast_payload, "api.ts", "services/db.ts") is True
        assert "near_miss_graph_gap" in caplog.text

    def test_dependency_edge_with_no_near_miss_still_returns_false(self, caplog):
        ast_payload = _ast_payload(dependency_graph=[])
        with caplog.at_level("WARNING"):
            assert verify_dependency_edge_exists(ast_payload, "a", "b") is False
        assert "near_miss_graph_gap" not in caplog.text
