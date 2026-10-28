"""
P0-9 follow-up: migrations were loose SQL files run by hand, so nothing
recorded which ones a project had applied. They are now also tracked by
the Supabase CLI: supabase/migrations/ holds a byte-identical copy of every
root migration, with timestamp prefixes in the original order. Nothing
here runs `supabase db push`; DEPLOY_RENDER.md says how to mark the
already-applied ones first.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TRACKED = REPO / "supabase" / "migrations"


def _root_migrations() -> list[Path]:
    def number(p: Path) -> int:
        m = re.match(r"migrations_(\d{3})_", p.name)
        return int(m.group(1)) if m else 1  # migrations.sql is the first
    return sorted(REPO.glob("migrations*.sql"), key=number)


def test_supabase_project_is_initialised():
    assert (REPO / "supabase" / "config.toml").is_file()


def test_every_root_migration_has_one_identical_timestamped_copy_in_order():
    root = _root_migrations()
    tracked = sorted(TRACKED.glob("*.sql"))
    assert len(tracked) == len(root)
    stamps = [p.name.split("_", 1)[0] for p in tracked]
    assert all(re.fullmatch(r"\d{14}", s) for s in stamps), stamps
    assert stamps == sorted(stamps) and len(set(stamps)) == len(stamps)
    for original, copy in zip(root, tracked):
        assert copy.read_bytes() == original.read_bytes(), (original.name, copy.name)


def test_deploy_guide_explains_tracked_migrations_without_pushing_blind():
    guide = (REPO / "docs" / "DEPLOY_RENDER.md").read_text()
    assert "supabase/migrations" in guide
    assert "supabase migration repair" in guide
    assert "supabase db push" in guide
