"""
Audit P1-10: the boundary spec used to be Ignition's own
ignition.boundaries.yaml (describing Ignition's code, and missing from the
image). It now comes from the customer's repo at the PR's base commit
(ASTAnalyzerPayload.boundary_spec_yaml), is parsed with yaml.safe_load onto
the review state, and is what agent_1_gate and the Critic use. No file
means an empty spec and one explanatory line in the comment.
"""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.graph.nodes import agent_3_critic as critic
from app.graph.nodes.agent_1_gate import agent_1_gate
from app.graph.state import Finding, ReviewState
import app.graph.verification.boundary_spec as boundary_spec_module
from app.schemas.ast_payload import ASTAnalyzerPayload, DependencyEdge

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = """
version: 1
layers:
  - name: repositories
    patterns: ["src/repositories/**"]
  - name: routes
    patterns: ["src/routes/**"]
rules:
  - from: repositories
    to: routes
    disallowed: true
"""


def load_boundary_spec(text):  # looked up per call so each test reports its own failure
    return boundary_spec_module.load_boundary_spec(text)


def _spec_error():
    return getattr(boundary_spec_module, "BoundarySpecError", type("BoundarySpecErrorMissing", (Exception,), {}))


EDGE = DependencyEdge(from_file="src/repositories/user.ts", to_file="src/routes/api.ts", imported_symbols=[])


def _state(spec_yaml):
    payload = ASTAnalyzerPayload(repo_full_name="acme/widgets", pr_number=1, changed_files=[EDGE.from_file],
                                 symbols=[], dependency_graph=[EDGE], boundary_spec_yaml=spec_yaml)
    return ReviewState(repo_full_name="acme/widgets", pr_number=1, installation_id=1, ast_payload=payload)


def test_load_boundary_spec_parses_the_customer_yaml():
    spec = load_boundary_spec(SPEC)
    assert [layer.name for layer in spec.layers] == ["repositories", "routes"]
    assert [(r.from_layer, r.to_layer, r.disallowed) for r in spec.rules] == [("repositories", "routes", True)]


@pytest.mark.parametrize("text", [None, "", "   \n", "# only a comment\n"])
def test_empty_yaml_is_an_empty_spec(text):
    spec = load_boundary_spec(text)
    assert spec.layers == [] and spec.rules == []


@pytest.mark.parametrize("text", [
    "layers: [",                                   # not YAML
    "- just\n- a list\n",                          # not a mapping
    "layers:\n  - patterns: ['a/**']\n",            # layer without a name
    "rules:\n  - to: routes\n",                    # rule without "from"
    "!!python/object/apply:os.system ['true']\n",  # safe_load refuses tags
])
def test_malformed_yaml_raises(text):
    with pytest.raises(_spec_error()):
        load_boundary_spec(text)


def test_state_carries_the_parsed_spec_and_notes_a_missing_or_bad_file():
    assert [layer.name for layer in _state(SPEC).boundary_spec.layers] == ["repositories", "routes"]
    assert _state(SPEC).boundary_spec_note is None
    missing = _state(None)
    assert missing.boundary_spec.layers == []
    assert missing.boundary_spec_note == "No ignition.boundaries.yaml found; boundary checks skipped"
    bad = _state("layers: [")
    assert bad.boundary_spec.layers == []
    assert bad.boundary_spec_note.startswith("ignition.boundaries.yaml could not be parsed")


def test_gate_uses_the_customer_spec_not_ignitions_own():
    assert agent_1_gate(_state(SPEC))["hard_rule_violation"] is True
    assert agent_1_gate(_state(None))["hard_rule_violation"] is False


@pytest.mark.asyncio
async def test_critic_fact_checks_against_the_customer_spec_and_explains_a_missing_one(monkeypatch):
    monkeypatch.setattr(critic, "LedgerRepository", lambda: MagicMock(
        get_baseline=lambda repo: None, get_consecutive_rejections=lambda p, r: 0))
    monkeypatch.setattr(critic, "VectorStore", lambda: MagicMock(record_incident=AsyncMock()))

    async def run(spec_yaml):
        state = _state(spec_yaml)
        state.findings = [Finding(agent="agent_2a_struct", file_path=EDGE.from_file, description="layer crossing",
                                  severity="medium", dependency_edge_ref=(EDGE.from_file, EDGE.to_file))]
        with patch.object(critic, "get_llm_client", return_value=MagicMock(complete=AsyncMock(return_value="n"))):
            return await critic.agent_3_critic(state)

    with_spec = await run(SPEC)
    assert with_spec["verified_findings"][0].verification_tier == "fact_checked"
    assert "boundary checks skipped" not in with_spec["final_comment_markdown"]

    without = await run(None)
    assert without["verified_findings"][0].verification_tier == "contextual"
    assert without["final_comment_markdown"].count("No ignition.boundaries.yaml found; boundary checks skipped") == 1


def test_ignitions_own_spec_is_now_the_example_template():
    assert not (REPO_ROOT / "ignition.boundaries.yaml").exists()
    template = REPO_ROOT / "docs" / "examples" / "ignition.boundaries.yaml"
    assert template.exists()
    assert load_boundary_spec(template.read_text()).rules
