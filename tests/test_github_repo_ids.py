"""
P2 "Repo ID collisions": the repositories row id was owner_name, so
acme_corp/api and acme/corp_api were the same repo to Ignition. Now the
webhook Repository schema carries GitHub's numeric `id`, migration 020 adds
github_repo_id to repositories and repository_settings, the settings routes
take the numeric ID, the review job loads settings by it, and
scripts/backfill_github_repo_ids.py fills existing rows.
"""
import importlib.util
import inspect
import re
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.repositories.dashboard import RepoRepository
from tests.fake_supabase import FakeSupabase

REPO_ROOT = Path(__file__).resolve().parents[1]
A, B = ("acme_corp/api", 101), ("acme/corp_api", 202)  # same owner_name id


def _db(**tables):
    unique = {"repositories": [(("id",), None), (("github_repo_id",), lambda r: r.get("github_repo_id") is not None)],
              "repository_settings": [(("repo_id",), None),
                                      (("github_repo_id",), lambda r: r.get("github_repo_id") is not None)]}
    return FakeSupabase({"repositories": [], "repository_settings": [], **tables}, unique=unique)


def _repo(db) -> RepoRepository:
    repo = RepoRepository.__new__(RepoRepository)
    repo._db = db
    return repo


def test_webhook_repository_schema_carries_the_numeric_id():
    from app.schemas.github import Repository
    repo = Repository.model_validate({"id": 202, "full_name": "acme/corp_api", "default_branch": "main",
                                      "clone_url": "https://github.com/acme/corp_api.git"})
    assert repo.id == 202


def test_migration_adds_unique_github_repo_id_to_both_tables():
    [path] = REPO_ROOT.glob("migrations_020_*.sql")
    sql = re.sub(r"\s+", " ", path.read_text())
    for table in ("repositories", "repository_settings"):
        assert f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS github_repo_id BIGINT UNIQUE;" in sql


def test_colliding_owner_name_repos_get_separate_rows_and_settings():
    db = _db()
    repos = _repo(db)
    repos.get_or_create_repo(A[0], github_repo_id=A[1])
    repos.get_or_create_repo(B[0], github_repo_id=B[1])
    assert sorted((r["owner"], r["name"], r["github_repo_id"]) for r in db.tables["repositories"]) == [
        ("acme", "corp_api", 202), ("acme_corp", "api", 101)]
    assert sorted(s["github_repo_id"] for s in db.tables["repository_settings"]) == [101, 202]

    repos.update_settings(202, {"enable_auto_fix": True})
    assert repos.get_or_create_settings(202)["enable_auto_fix"] is True
    assert repos.get_or_create_settings(101)["enable_auto_fix"] is False


def test_repo_list_reports_the_numeric_id_and_both_colliding_repos():
    db = _db()
    repos = _repo(db)
    repos.get_or_create_repo(A[0], github_repo_id=A[1])
    repos.get_or_create_repo(B[0], github_repo_id=B[1])
    listed = repos.list_repos(repo_names=frozenset({A[0], B[0]}))
    assert sorted((f"{r['owner']}/{r['name']}", r["id"]) for r in listed) == [(B[0], "202"), (A[0], "101")]


def test_a_legacy_row_is_adopted_not_duplicated():
    db = _db(repositories=[{"id": "acme_widgets", "owner": "acme", "name": "widgets", "language": "TypeScript"}],
             repository_settings=[{"repo_id": "acme_widgets", "enable_ai_review": True, "enable_auto_fix": True,
                                   "enable_hitl": True, "security_scan": True, "architecture_scan": True,
                                   "logic_scan": True}])
    repos = _repo(db)
    repos.get_or_create_repo("acme/widgets", github_repo_id=7)
    assert [(r["id"], r["github_repo_id"]) for r in db.tables["repositories"]] == [("acme_widgets", 7)]
    assert repos.get_or_create_settings(7)["enable_auto_fix"] is True  # the owner's saved choice survives


def test_installed_flag_and_stats_never_touch_the_colliding_repo():
    db = _db()
    repos = _repo(db)
    repos.get_or_create_repo(A[0], github_repo_id=A[1])
    repos.get_or_create_repo(B[0], github_repo_id=B[1])
    repos.set_repo_installed(B[0], False)
    repos.update_repo_stats(B[0], 42.0, "2026-10-28T00:00:00+00:00")
    by_id = {r["github_repo_id"]: r for r in db.tables["repositories"]}
    assert by_id[202].get("installed") is False and by_id[202]["acs_score"] == 42.0
    assert by_id[101].get("installed") is not False and by_id[101].get("acs_score") is None


def test_settings_routes_take_the_numeric_id():
    import app.main as main_module
    for fn in (main_module.get_repo_settings, main_module.update_repo_settings):
        assert inspect.signature(fn).parameters["repo_id"].annotation is int


@pytest.mark.asyncio
async def test_access_check_resolves_the_numeric_id_to_its_own_repo(monkeypatch):
    import app.auth as auth_module
    db = _db()
    repos = _repo(db)
    repos.get_or_create_repo(A[0], github_repo_id=A[1])
    repos.get_or_create_repo(B[0], github_repo_id=B[1])
    monkeypatch.setattr(auth_module._repo_repo, "_db", db)
    check = AsyncMock()
    monkeypatch.setattr(auth_module, "check_repo_access", check)
    await auth_module.require_repo_id_access(object(), 202, user=object())
    check.assert_awaited_once()
    assert check.await_args.args[1] == B[0]


def _backfill():
    path = REPO_ROOT / "scripts" / "backfill_github_repo_ids.py"
    spec = importlib.util.spec_from_file_location("backfill_github_repo_ids", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_backfill_fills_both_tables_once_and_reports_missing_repos():
    db = _db(repositories=[{"id": "acme_widgets", "owner": "acme", "name": "widgets"},
                           {"id": "acme_gone", "owner": "acme", "name": "gone"},
                           {"id": "999", "owner": "acme", "name": "done", "github_repo_id": 999}],
             repository_settings=[{"repo_id": "acme_widgets"}, {"repo_id": "acme_gone"},
                                  {"repo_id": "999", "github_repo_id": 999}])
    calls = []

    def lookup(full_name):
        calls.append(full_name)
        return {"acme/widgets": 7}.get(full_name)

    report = _backfill().backfill(db, lookup)
    assert calls == ["acme/gone", "acme/widgets"]  # rows already filled aren't looked up
    assert report == {"filled": 1, "not_found": ["acme/gone"]}
    for table, key in (("repositories", "id"), ("repository_settings", "repo_id")):
        assert {r[key]: r.get("github_repo_id") for r in db.tables[table]} == {
            "acme_widgets": 7, "acme_gone": None, "999": 999}
    assert _backfill().backfill(db, lookup) == {"filled": 0, "not_found": ["acme/gone"]}


def test_startup_check_names_a_missing_github_repo_id_column():
    from app.services import schema_check

    class Db(FakeSupabase):
        def table(self, name):
            query = super().table(name)
            select = query.select

            def checked(*cols, **kw):
                if name == "repositories" and cols == ("github_repo_id",):
                    raise RuntimeError("column repositories.github_repo_id does not exist")
                return select(*cols, **kw)
            query.select = checked
            return query

    assert schema_check.find_missing_tables(Db()) == ["repositories.github_repo_id"]
