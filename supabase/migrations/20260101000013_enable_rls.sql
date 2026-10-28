-- Audit P1-2: no row-level security. Every table in `public` was readable
-- and writable by anyone holding the project's anon key (it ships in
-- Supabase's client SDKs and is not a secret).
--
-- No policies are needed: only the backend talks to Supabase, and it uses
-- the service_role key, which bypasses RLS. BEFORE RUNNING: confirm
-- SUPABASE_SERVICE_KEY really holds the service_role key (decode its JWT
-- payload and check "role": "service_role") — if it holds the anon key,
-- running this cuts the backend off too. See docs/readiness/HUMAN_ACTIONS.md.
--
-- Run once now, and again after every migration that creates a new table.

DO $$
DECLARE t record;
BEGIN
  FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t.tablename);
  END LOOP;
END $$;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
REVOKE EXECUTE ON FUNCTION match_incident_embeddings(vector, text, int) FROM anon, authenticated, public;
