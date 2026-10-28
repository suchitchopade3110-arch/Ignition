"""
Blocking pip-audit for CI (I-12): audits requirements.txt and fails on any
known vulnerability, except IDs listed in .github/pip-audit-ignore.txt.

Each ignore line is `<vuln id>  # <reason>`; a line without a reason is an
error, so nothing gets ignored silently. Usage:

    python scripts/run_pip_audit.py [requirements.txt]
"""
import subprocess
import sys
from pathlib import Path

IGNORE_FILE = Path(__file__).resolve().parents[1] / ".github" / "pip-audit-ignore.txt"


def read_ignore_list(path: Path) -> list[tuple[str, str]]:
    entries = []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        vuln_id, _, reason = line.partition("#")
        vuln_id, reason = vuln_id.strip(), reason.strip()
        if not reason:
            raise ValueError(f"{path}: {vuln_id} has no reason (write `{vuln_id}  # why`)")
        entries.append((vuln_id, reason))
    return entries


def pip_audit_args(ignore_file: Path, requirements: str) -> list[str]:
    args = ["pip-audit", "-r", requirements, "--strict"]
    for vuln_id, _ in read_ignore_list(ignore_file):
        args += ["--ignore-vuln", vuln_id]
    return args


def main() -> int:
    requirements = sys.argv[1] if len(sys.argv) > 1 else "requirements.txt"
    args = pip_audit_args(IGNORE_FILE, requirements)
    print("+", " ".join(args), flush=True)
    return subprocess.call(args)


if __name__ == "__main__":
    sys.exit(main())
