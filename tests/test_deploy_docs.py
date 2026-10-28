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
