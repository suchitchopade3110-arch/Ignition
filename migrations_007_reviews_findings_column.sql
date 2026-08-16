-- Another pre-existing schema-drift gap surfaced while verifying a real
-- end-to-end run (Arq/Redis migration, Phase 2 Prompt 2): the critic
-- pipeline step writes a `findings` key via update_review(), and
-- ReviewRepository._map_review_row() already reads `row.get("findings")`
-- back out — but migrations.sql only ever defined `verified_findings`,
-- never `findings`. Never triggered before because no run in this
-- (Phase-1-recreated) Supabase project had reached this step successfully
-- until now.

ALTER TABLE reviews ADD COLUMN findings JSONB DEFAULT '[]'::jsonb;
