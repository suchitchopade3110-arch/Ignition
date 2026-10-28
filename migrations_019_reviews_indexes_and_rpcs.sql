-- I-10 (database work) and the P2 "IVFFlat on an empty table" item.

-- The dashboard's list and stats queries filter by status or repo and sort
-- by recency.
CREATE INDEX IF NOT EXISTS reviews_status_created_idx ON reviews (status, created_at DESC);
CREATE INDEX IF NOT EXISTS reviews_repo_created_idx ON reviews (repo_full_name, created_at DESC);

-- Dashboard stats for a set of repos in one query (was: four queries and
-- the averaging done in Python over every row).
CREATE OR REPLACE FUNCTION dashboard_stats(repo_names text[]) RETURNS json LANGUAGE sql STABLE AS $$
  SELECT json_build_object(
    'activeReviews', count(*) FILTER (WHERE status = 'running'),
    'hitlPending',   count(*) FILTER (WHERE status = 'waiting_hitl'),
    'avgAcsScore',   coalesce(round(avg(acs_score) FILTER (WHERE status = 'completed')::numeric, 1), 0),
    'issuesFound',   coalesce(sum(findings_count), 0))
  FROM reviews WHERE repo_full_name = ANY(repo_names);
$$;
REVOKE EXECUTE ON FUNCTION dashboard_stats(text[]) FROM anon, authenticated, public;

-- Each repo's latest review in one query (was: one query per repo).
CREATE OR REPLACE FUNCTION latest_review_per_repo(repo_names text[])
RETURNS TABLE (repo_full_name text, acs_score numeric, status review_status, created_at timestamptz)
LANGUAGE sql STABLE AS $$
  SELECT DISTINCT ON (r.repo_full_name) r.repo_full_name, r.acs_score, r.status, r.created_at
  FROM reviews r
  WHERE r.repo_full_name = ANY(repo_names)
  ORDER BY r.repo_full_name, r.created_at DESC;
$$;
REVOKE EXECUTE ON FUNCTION latest_review_per_repo(text[]) FROM anon, authenticated, public;

-- Retention: drop stored diffs from reviews older than N days (the worker
-- runs this daily). Returns how many rows changed.
CREATE OR REPLACE FUNCTION prune_review_diffs(older_than_days int DEFAULT 30) RETURNS integer LANGUAGE sql AS $$
  WITH pruned AS (
    UPDATE reviews SET diff_text = NULL, diffs = NULL
    WHERE created_at < now() - make_interval(days => older_than_days)
      AND (diff_text IS NOT NULL OR diffs IS NOT NULL)
    RETURNING 1
  )
  SELECT count(*)::int FROM pruned;
$$;
REVOKE EXECUTE ON FUNCTION prune_review_diffs(int) FROM anon, authenticated, public;

-- HNSW works on an empty table and needs no training; IVFFlat built on an
-- empty table clusters nothing.
DROP INDEX IF EXISTS incident_embeddings_vector_idx;
CREATE INDEX incident_embeddings_vector_idx ON incident_embeddings USING hnsw (embedding vector_cosine_ops);
