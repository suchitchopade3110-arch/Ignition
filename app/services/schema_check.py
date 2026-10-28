"""
Startup check that every Supabase table the code reads actually exists
(audit P0-9 follow-up). A deploy that skipped a migration used to start
fine and then fail every review that reached the missing table; now both
entrypoints (app/main.py's lifespan, app/worker.py's on_startup) refuse to
start, so the platform's health check fails the deploy instead.
"""
import logging

from app.database import get_supabase

logger = logging.getLogger(__name__)

REQUIRED_TABLES = (
    "repositories",
    "repository_settings",
    "reviews",
    "users",
    "sessions",
    "architecture_ledger",
    "incident_embeddings",
    "hitl_finding_outcomes",
)


def find_missing_tables(db) -> list[str]:
    """Tables that can't be read. limit(0) returns no rows, so this costs one
    cheap round-trip per table. An unreachable database reports every table:
    failing closed is the point."""
    missing = []
    for table in REQUIRED_TABLES:
        try:
            db.table(table).select("*").limit(0).execute()
        except Exception as exc:
            logger.error("Required table check failed", extra={"table": table, "error_class": type(exc).__name__})
            missing.append(table)
    return missing


def require_tables_or_exit(db=None) -> None:
    missing = find_missing_tables(db if db is not None else get_supabase())
    if missing:
        logger.critical(
            "Required Supabase tables are missing or unreadable: %s. Run the migrations "
            "(docs/DEPLOY_RENDER.md) before starting this service.",
            ", ".join(missing),
        )
        raise SystemExit(1)
