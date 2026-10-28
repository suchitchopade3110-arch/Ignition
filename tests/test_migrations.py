"""
Static checks on the SQL migration files. They don't need a database: they
pin down that each audit fix's SQL is present and shaped as the solutions
doc specifies. (The run's evidence also applies every migration to a
throwaway local Postgres 16 + pgvector; that is not part of CI.)
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _sql(number: int) -> str:
    [path] = REPO_ROOT.glob(f"migrations_{number:03d}_*.sql")
    return re.sub(r"\s+", " ", path.read_text())


def test_rls_migration_enables_rls_on_every_public_table_and_revokes_anon():
    sql = _sql(13)
    assert "FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP" in sql
    assert "EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t.tablename);" in sql
    assert "REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;" in sql
    assert ("REVOKE EXECUTE ON FUNCTION match_incident_embeddings(vector, text, int) "
            "FROM anon, authenticated, public;") in sql
    assert "CREATE POLICY" not in sql.upper()  # service_role bypasses RLS; no policies by design


def test_hitl_outcomes_index_matches_the_repo_scoped_rejection_query():
    sql = _sql(14)
    assert "ON hitl_finding_outcomes (repo_full_name, pattern_key, created_at DESC)" in sql


def test_review_status_gains_posting_and_rejected():
    sql = _sql(15)
    assert "ALTER TYPE review_status ADD VALUE IF NOT EXISTS 'posting';" in sql
    assert "ALTER TYPE review_status ADD VALUE IF NOT EXISTS 'rejected';" in sql


def test_reviews_gain_a_check_run_id():
    assert "ALTER TABLE reviews ADD COLUMN IF NOT EXISTS check_run_id BIGINT;" in _sql(16)


def test_dedupe_index_becomes_partial_and_reviews_can_be_requeued():
    # I-4: a failed or cancelled review can be redelivered for the same SHA;
    # reconciliation needs the original event to re-enqueue and a timestamp
    # for a stuck "posting" claim.
    sql = _sql(18)
    assert "DROP INDEX IF EXISTS reviews_repo_pr_head_sha_uidx;" in sql
    assert ("CREATE UNIQUE INDEX reviews_repo_pr_head_sha_uidx ON reviews (repo_full_name, pr_number, commit_sha) "
            "WHERE status NOT IN ('failed', 'cancelled');") in sql
    assert "ALTER TABLE reviews ADD COLUMN IF NOT EXISTS event_payload JSONB;" in sql
    assert "ALTER TABLE reviews ADD COLUMN IF NOT EXISTS status_changed_at TIMESTAMP WITH TIME ZONE;" in sql
