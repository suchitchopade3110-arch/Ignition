"""
I-12: dependency audits block CI. The dependency-audit job runs
`npm audit --audit-level=high` (frontend), `bun audit --audit-level=high`
(ast-analyzer) and pip-audit on requirements.txt with an in-repo ignore
list, and none of them may be allowed to fail.
"""
import importlib.util
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
CI = yaml.safe_load((REPO / ".github" / "workflows" / "ci.yml").read_text())
AUDIT_STEPS = CI["jobs"]["dependency-audit"]["steps"]
IGNORE_FILE = REPO / ".github" / "pip-audit-ignore.txt"


def _step(command_fragment: str) -> dict:
    matches = [s for s in AUDIT_STEPS if command_fragment in s.get("run", "")]
    assert len(matches) == 1, f"expected one step running {command_fragment!r}, got {matches}"
    return matches[0]


def _runner():
    path = REPO / "scripts" / "run_pip_audit.py"
    spec = importlib.util.spec_from_file_location("run_pip_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("command, workdir", [
    ("npm audit --audit-level=high", "frontend"),
    ("bun audit --audit-level=high", "ast-analyzer"),
    ("python scripts/run_pip_audit.py", None),
])
def test_each_audit_runs_and_blocks(command, workdir):
    step = _step(command)
    assert step.get("working-directory") == workdir
    assert not step.get("continue-on-error"), step
    assert "|| true" not in step["run"] and "|| exit 0" not in step["run"]


def test_no_audit_step_is_allowed_to_fail():
    assert not CI["jobs"]["dependency-audit"].get("continue-on-error")
    assert not any(s.get("continue-on-error") for s in AUDIT_STEPS)


def test_the_ignore_list_lives_in_the_repo_and_every_entry_has_a_reason():
    assert IGNORE_FILE.exists()
    entries = _runner().read_ignore_list(IGNORE_FILE)  # raises on an entry without a reason
    assert all(reason for _, reason in entries)


def test_the_runner_passes_each_ignored_id_to_pip_audit(tmp_path):
    ignore = tmp_path / "ignore.txt"
    ignore.write_text(
        "# comment line\n"
        "\n"
        "GHSA-aaaa-bbbb-cccc  # not reachable: we never parse untrusted images\n"
        "CVE-2099-1  # fix not released yet; recheck 2099-02-01\n"
    )
    args = _runner().pip_audit_args(ignore, "requirements.txt")
    assert args == ["pip-audit", "-r", "requirements.txt", "--strict",
                    "--ignore-vuln", "GHSA-aaaa-bbbb-cccc", "--ignore-vuln", "CVE-2099-1"]


def test_an_entry_without_a_reason_is_rejected(tmp_path):
    ignore = tmp_path / "ignore.txt"
    ignore.write_text("CVE-2099-1\n")
    with pytest.raises(ValueError, match="CVE-2099-1"):
        _runner().read_ignore_list(ignore)
