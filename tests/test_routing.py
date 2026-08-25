from app.graph.routing import route_after_gate, route_after_critic, route_hitl
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


def test_route_after_critic_retries_when_requested_and_under_cap():
    state = _base_state(critic_wants_retry=True, hallucination_retry_count=0)
    assert route_after_critic(state) == "retry_context_fetch"


def test_route_after_critic_stops_retrying_once_cap_reached():
    from app.config import get_settings
    cap = get_settings().hallucination_retry_cap
    state = _base_state(critic_wants_retry=True, hallucination_retry_count=cap)
    assert route_after_critic(state) == "route_hitl"


def test_route_after_critic_does_not_retry_when_not_requested():
    state = _base_state(critic_wants_retry=False, acs_score=90.0)
    assert route_after_critic(state) == "route_hitl"