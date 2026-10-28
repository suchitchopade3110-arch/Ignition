-- Two tables that app/repositories/ledger.py and app/repositories/
-- embeddings.py have always expected but were never part of migrations.sql
-- in this repo snapshot — surfaced as real crashes (agent_3_critic reading
-- architecture_ledger) while verifying the Arq/Redis migration end-to-end
-- against the Supabase project recreated during Phase 1. Not something
-- that migration caused; just the first time a real run reached this code
-- path since the project was recreated.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE architecture_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_full_name TEXT NOT NULL,
    acs_score NUMERIC(5,2) NOT NULL,
    risk_scores JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);
CREATE INDEX architecture_ledger_repo_created_idx
    ON architecture_ledger (repo_full_name, created_at DESC);

-- 384-dim to match sentence-transformers/all-MiniLM-L6-v2's output
-- exactly (see app/rag/vector_store.py's own comment on this) — any
-- mismatch here fails every insert/query outright.
CREATE TABLE incident_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_full_name TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(384) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);
CREATE INDEX incident_embeddings_repo_idx ON incident_embeddings (repo_full_name);
-- IVFFlat needs rows to train on; fine to create the index empty here and
-- let Supabase/Postgres use a sequential scan until enough rows exist.
CREATE INDEX incident_embeddings_vector_idx
    ON incident_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- app/rag/vector_store.py::similar_incidents calls this by name via
-- .rpc(); it didn't exist at all before this migration.
CREATE OR REPLACE FUNCTION match_incident_embeddings(
    query_embedding VECTOR(384),
    match_repo TEXT,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    repo_full_name TEXT,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE sql STABLE
AS $$
    SELECT
        id,
        repo_full_name,
        content,
        metadata,
        1 - (embedding <=> query_embedding) AS similarity
    FROM incident_embeddings
    WHERE repo_full_name = match_repo
    ORDER BY embedding <=> query_embedding
    LIMIT match_count;
$$;
