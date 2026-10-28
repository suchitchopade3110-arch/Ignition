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


# Read-only SQL functions the dashboard calls (migrations_019, I-10), with
# arguments that touch no rows. Reported as "rpc:<name>".
REQUIRED_FUNCTIONS = {
    "dashboard_stats": {"repo_names": []},
    "latest_review_per_repo": {"repo_names": []},
}


# Columns added to existing tables that the code keys on (migrations_020,
# P2 repo IDs). Reported as "<table>.<column>".
REQUIRED_COLUMNS = (
    ("repositories", "github_repo_id"),
    ("repository_settings", "github_repo_id"),
)


def find_missing_tables(db) -> list[str]:
    """Tables (and SQL functions) that can't be used. limit(0) returns no
    rows, so this costs one cheap round-trip per table. An unreachable
    database reports every one: failing closed is the point."""
    missing = []
    for table in REQUIRED_TABLES:
        try:
            db.table(table).select("*").limit(0).execute()
        except Exception as exc:
            logger.error("Required table check failed", extra={"table": table, "error_class": type(exc).__name__})
            missing.append(table)
    for table, column in REQUIRED_COLUMNS:
        if table in missing:
            continue
        try:
            db.table(table).select(column).limit(0).execute()
        except Exception as exc:
            logger.error("Required column check failed",
                         extra={"table": table, "column": column, "error_class": type(exc).__name__})
            missing.append(f"{table}.{column}")
    for function, params in REQUIRED_FUNCTIONS.items():
        try:
            db.rpc(function, params).execute()
        except Exception as exc:
            logger.error("Required function check failed",
                         extra={"function": function, "error_class": type(exc).__name__})
            missing.append(f"rpc:{function}")
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
