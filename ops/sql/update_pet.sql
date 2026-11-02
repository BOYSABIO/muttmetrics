-- Recipe: enrich pet hand-entered fields (coat / temperament / weight / medical).
-- See docs/runbooks/enrichment.md — "Enrich a pet".
-- For breed_id only, prefer enrich_pet_breed.sql.
-- Do NOT set size_band, visit_count, last_visit_date, avg_duration_min, etc.

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
  sex = 'F',
  coat_type = 'curly',                 -- free text / your convention
  hair_or_fur = 'hair',
  coat_density = 'medium',
  undercoat = true,
  sheds = false,
  handling_score = 3,                  -- 1–5 CHECK
  fear_triggers = ARRAY['dryer'],      -- TEXT[]
  muzzle_required = false,
  two_person_job = false,
  temperament_notes = 'Example note',
  senior_flag = false,
  mobility_notes = NULL,
  vet_notes = NULL
WHERE pet_id = 123;

-- ---------------------------------------------------------------------------
-- 3) Verify
-- ---------------------------------------------------------------------------
SELECT pet_id, name, weight_kg, coat_type, handling_score, fear_triggers, temperament_notes
FROM pet
WHERE pet_id = 123;

COMMIT;
