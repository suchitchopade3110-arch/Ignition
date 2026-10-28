"""
Audit P0-9 follow-up: a deploy that skipped a migration must fail at
startup (and so fail its health check), not fail reviews later. Both
entrypoints — the FastAPI app and the Arq worker — check every table the
code reads with select("*").limit(0) and exit non-zero, naming what is
missing.
"""
import importlib
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from postgrest.exceptions import APIError


def _db(missing: set[str]) -> MagicMock:
    db = MagicMock()

    def table(name):
        query = MagicMock()
        if name in missing:
            query.select.return_value.limit.return_value.execute.side_effect = APIError(
                {"code": "PGRST205", "message": f"Could not find the table 'public.{name}' in the schema cache"}
            )
        return query

    db.table.side_effect = table
    return db


def test_missing_tables_are_reported_by_name():
    schema_check = importlib.import_module("app.services.schema_check")
    assert schema_check.find_missing_tables(_db({"hitl_finding_outcomes"})) == ["hitl_finding_outcomes"]
    assert schema_check.find_missing_tables(_db(set())) == []


def test_required_tables_cover_every_table_the_code_reads():
    schema_check = importlib.import_module("app.services.schema_check")
    assert set(schema_check.REQUIRED_TABLES) >= {
        "repositories", "repository_settings", "reviews", "users", "sessions",
        "architecture_ledger", "incident_embeddings", "hitl_finding_outcomes",
    }


def test_missing_table_exits_non_zero_and_logs_it(caplog):
    schema_check = importlib.import_module("app.services.schema_check")
    with caplog.at_level(logging.CRITICAL), pytest.raises(SystemExit) as exc_info:
        schema_check.require_tables_or_exit(_db({"hitl_finding_outcomes", "sessions"}))
    assert exc_info.value.code == 1
    assert "hitl_finding_outcomes" in caplog.text and "sessions" in caplog.text


@pytest.mark.asyncio
async def test_web_app_startup_runs_the_table_check():
    import app.main as main_module

    with patch.object(main_module, "require_tables_or_exit", side_effect=SystemExit(1), create=True) as check:
        with pytest.raises(SystemExit):
            async with main_module.app.router.lifespan_context(main_module.app):
                pass
    check.assert_called_once()


@pytest.mark.asyncio
async def test_worker_startup_checks_tables_before_reconciling():
    import app.worker as worker_module

    reconcile = AsyncMock()
    with patch.object(worker_module, "require_tables_or_exit", side_effect=SystemExit(1), create=True), \
         patch.object(worker_module, "reconcile_orphaned_reviews", reconcile):
        with pytest.raises(SystemExit):
            await worker_module.on_startup({})
    reconcile.assert_not_awaited()
