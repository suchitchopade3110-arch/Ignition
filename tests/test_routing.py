from app.graph.routing import route_after_gate, route_hitl
from app.graph.state import ReviewState
from app.schemas.ast_payload import ASTAnalyzerPayload


def _base_state(**overrides) -> ReviewState:
    defaults = dict(
        repo_full_name="acme/widgets",
        pr_number=1,
        installation_id=12345,
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=1,
            changed_files=[],
            symbols=[],
            dependency_graph=[],
        ),
    )
    defaults.update(overrides)
    return ReviewState(**defaults)


def test_route_after_gate_rejects_on_violation():
    state = _base_state(hard_rule_violation=True)
    assert route_after_gate(state) == "direct_rejection"


def test_route_after_gate_fans_out_when_clean():
    state = _base_state(hard_rule_violation=False)
    assert route_after_gate(state) == "fan_out"


def test_route_hitl_pauses_on_critical():
    state = _base_state(hitl_severity="critical")
    assert route_hitl(state) == "pause_for_human_approval"


def test_route_hitl_continues_on_non_critical():
    state = _base_state(hitl_severity="medium")
    assert route_hitl(state) == "finalize_and_post"