"""
Every script in scripts/ is run as `python scripts/<name>.py` (CI's
golden-eval job, DEPLOY_RENDER.md, HUMAN_ACTIONS). Run that way, Python
puts scripts/ on sys.path, not the repo root, so a bare `from app...`
import fails. Each script must make its own imports work: this loads it
by path with the repo root off sys.path, without running its main.
"""
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = sorted(p.name for p in (REPO / "scripts").glob("*.py"))

LOADER = (
    "import runpy, sys; "
    "sys.path[:] = [p for p in sys.path if p not in ('', '.', sys.argv[2])]; "
    "sys.path.insert(0, sys.argv[2] + '/scripts'); "
    "runpy.run_path(sys.argv[1], run_name='imported_for_check')"
)


@pytest.mark.parametrize("script", SCRIPTS)
def test_script_imports_resolve_when_run_by_path(script):
    env = {"PATH": "/usr/bin:/bin", "GITHUB_APP_ID": "1", "GITHUB_WEBHOOK_SECRET": "x", "LLM_API_KEY": "x",
           "SUPABASE_URL": "https://dummy-project.supabase.co", "SUPABASE_SERVICE_KEY": "x"}
    proc = subprocess.run([sys.executable, "-c", LOADER, str(REPO / "scripts" / script), str(REPO)],
                          cwd=REPO / "scripts", env=env, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr[-1500:]
