"""
Audit P0-9: docs/DEPLOY_RENDER.md told operators to run migrations only up
to 011 while the code already needed 012, so every review with a finding
failed on a fresh deploy. These checks keep the guide in step with the
migration files and the live model default.
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GUIDE = (REPO_ROOT / "docs" / "DEPLOY_RENDER.md").read_text()


def test_deploy_guide_names_the_latest_migration():
    numbers = [int(m.group(1)) for p in REPO_ROOT.glob("migrations_*.sql")
               if (m := re.match(r"migrations_(\d{3})_", p.name))]
    latest = f"migrations_{max(numbers):03d}_"
    assert latest in GUIDE, f"DEPLOY_RENDER.md must tell operators to run migrations through {latest}"


def test_deploy_guide_does_not_suggest_the_shut_down_model():
    assert "qwen/qwen3-32b" not in GUIDE
    assert "openai/gpt-oss-120b" in GUIDE and "LLM_REASONING_EFFORT" in GUIDE


def test_every_llm_service_in_the_blueprint_declares_model_and_reasoning_effort():
    import yaml

    blueprint = yaml.safe_load((REPO_ROOT / "render.yaml").read_text())
    llm_services = [s for s in blueprint["services"]
                    if any(e.get("key") == "LLM_API_KEY" for e in s.get("envVars", []))]
    assert llm_services, "no service in render.yaml declares LLM_API_KEY"
    for service in llm_services:
        keys = {e.get("key") for e in service.get("envVars", [])}
        assert {"LLM_MODEL_NAME", "LLM_REASONING_EFFORT"} <= keys, service["name"]
