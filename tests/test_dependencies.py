"""
Solutions doc, "Dependency fixes": security floors must hold in the hashed
production lockfile, and test runners must not ship in it (P2 "pytest in
production").
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _pins(name: str) -> dict[str, tuple[int, ...]]:
    pins = {}
    for line in (REPO_ROOT / name).read_text().splitlines():
        m = re.match(r"^([A-Za-z0-9_.-]+)==([0-9][0-9.]*)", line)
        if m:
            pins[m.group(1).lower()] = tuple(int(p) for p in m.group(2).split(".") if p.isdigit())
    return pins


def test_security_floors_hold_in_the_production_lockfile():
    pins = _pins("requirements.txt")
    assert pins["pyjwt"] >= (2, 15, 0)
    assert pins["urllib3"] >= (2, 8, 0)
    assert (6, 9, 1) <= pins["multidict"] < (7,)


def test_test_runners_are_dev_only():
    assert "pytest" not in _pins("requirements.txt")
    assert "pytest-asyncio" not in _pins("requirements.txt")
    dev = _pins("requirements-dev.txt")
    assert "pytest" in dev and "pytest-asyncio" in dev
