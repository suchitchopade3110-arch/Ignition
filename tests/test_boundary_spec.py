from app.graph.verification.boundary_spec import (
    BoundaryLayer,
    BoundaryRule,
    BoundarySpec,
    check_boundary_violations,
    find_layer,
    is_boundary_violation,
    load_default_boundary_spec,
)
from app.schemas.ast_payload import DependencyEdge


def _spec() -> BoundarySpec:
    return BoundarySpec(
        layers=[
            BoundaryLayer(name="repositories", patterns=["app/repositories/**"]),
            BoundaryLayer(name="routes", patterns=["app/main.py", "app/api/**"]),
            BoundaryLayer(name="services", patterns=["app/services/**"]),
        ],
        rules=[
            BoundaryRule(from_layer="repositories", to_layer="routes", disallowed=True),
        ],
    )


class TestFindLayer:
    def test_matches_double_star_glob(self):
        spec = _spec()
        assert find_layer(spec, "app/repositories/ledger.py") == "repositories"

    def test_matches_exact_file_pattern(self):
        spec = _spec()
        assert find_layer(spec, "app/main.py") == "routes"

    def test_unmatched_file_returns_none(self):
        spec = _spec()
        assert find_layer(spec, "app/graph/state.py") is None

    def test_windows_style_separators_are_normalized(self):
        spec = _spec()
        assert find_layer(spec, "app\\repositories\\ledger.py") == "repositories"


class TestIsBoundaryViolation:
    def test_disallowed_direction_is_a_violation(self):
        spec = _spec()
        violation = is_boundary_violation(spec, "app/repositories/ledger.py", "app/main.py")
        assert violation is not None
        assert violation.from_layer == "repositories"
        assert violation.to_layer == "routes"

    def test_allowed_direction_is_not_a_violation(self):
        # routes -> repositories has no rule declared, so it's not flagged.
        spec = _spec()
        assert is_boundary_violation(spec, "app/main.py", "app/repositories/ledger.py") is None

    def test_edge_between_unmapped_files_is_not_a_violation(self):
        spec = _spec()
        assert is_boundary_violation(spec, "app/graph/state.py", "app/graph/scoring.py") is None

    def test_edge_between_layers_with_no_rule_is_not_a_violation(self):
        spec = _spec()
        assert is_boundary_violation(spec, "app/repositories/ledger.py", "app/services/llm_client.py") is None


class TestCheckBoundaryViolations:
    def test_only_disallowed_edges_are_reported(self):
        spec = _spec()
        graph = [
            DependencyEdge(from_file="app/repositories/ledger.py", to_file="app/main.py", imported_symbols=[]),
            DependencyEdge(from_file="app/repositories/ledger.py", to_file="app/services/llm_client.py", imported_symbols=[]),
        ]
        violations = check_boundary_violations(graph, spec)
        assert len(violations) == 1
        assert violations[0].from_file == "app/repositories/ledger.py"
        assert violations[0].to_file == "app/main.py"

    def test_empty_spec_flags_nothing(self):
        graph = [DependencyEdge(from_file="a.ts", to_file="b.ts", imported_symbols=[])]
        assert check_boundary_violations(graph, BoundarySpec()) == []


def test_load_default_boundary_spec_reads_repo_root_yaml():
    # ignition.boundaries.yaml ships in the repo root with a real
    # repositories -> routes rule — this is a smoke test that the loader
    # actually parses it, not just the in-memory fixtures above.
    spec = load_default_boundary_spec()
    assert any(layer.name == "repositories" for layer in spec.layers)
    assert any(
        rule.from_layer == "repositories" and rule.to_layer == "routes" and rule.disallowed
        for rule in spec.rules
    )
