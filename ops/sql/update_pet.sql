-- Recipe: enrich pet hand-entered fields (coat / temperament / weight / medical).
-- See docs/runbooks/enrichment.md — "Enrich a pet".
-- For breed_id only, prefer enrich_pet_breed.sql.
-- Do NOT set visit_count, last_visit_date, avg_duration_min, etc.
-- Size by eye (no weight): set size_band = 's'|'m'|'l'|'xl' AND size_source = 'eye' together.
-- SQL edits skip the pet_change log; prefer the app for anything a model will read.

-- ---------------------------------------------------------------------------
-- 1) Inspect
-- ---------------------------------------------------------------------------
SELECT
  d.pet_id,
  d.name,
  d.weight_kg,
  d.coat_type,
  d.handling_score,
  d.temperament_notes,
  o.name AS owner_name
FROM pet d
JOIN owner o ON o.owner_id = d.owner_id
WHERE d.pet_id = 123;   -- <-- placeholder pet_id

-- ---------------------------------------------------------------------------
-- 2) UPDATE — comment out anything you are not changing
-- ---------------------------------------------------------------------------
BEGIN;

UPDATE pet
SET
  weight_kg = 12.5,                    -- <-- size_band is NOT updated by SQL: run ops/backfill_size_band.py --apply after (#171)
  sex = 'female',                      -- 'female' | 'male' | NULL (unknown)
  coat_type = 'curly',                 -- dog: smooth|double|curly|wire|silky|combination; cat: short|long (CHECK, pet_vocab.py)
  coat_thickness = 2,                  -- 1 thin, 2 normal, 3 thick
  handling_score = 3,                  -- 1 easy .. 5 very difficult (CHECK)
  muzzle_required = false,             -- NULL = nobody checked; false = checked, not needed
  two_person_job = false,
  usual_cut = 'Example: teddy face, 1 cm body',
  temperament_notes = 'Example note',
  senior_flag = false,
  health_notes = NULL
WHERE pet_id = 123;

-- ---------------------------------------------------------------------------
-- 3) Verify
-- ---------------------------------------------------------------------------
SELECT pet_id, name, weight_kg, size_band, size_source, coat_type, coat_thickness, handling_score, usual_cut
FROM pet
WHERE pet_id = 123;

COMMIT;
