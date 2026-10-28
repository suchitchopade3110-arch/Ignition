-- Same class of pre-existing schema-drift gap as migrations_007: the
-- critic pipeline step writes a `hitl_severity` key via update_review()
-- (distinct from the existing `severity` column, both set from the same
-- value in app/services/review_pipeline.py) but this column never existed
-- in migrations.sql. Last of the gaps surfaced while verifying a real
-- end-to-end run through to completion — checked every key ever passed to
-- update_review()/create_review() against live columns after this one, no
-- further gaps found.

ALTER TABLE reviews ADD COLUMN hitl_severity TEXT;
