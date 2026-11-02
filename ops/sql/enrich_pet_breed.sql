-- Recipe: set pet.breed_id (and optional breed_secondary_id).
-- See docs/runbooks/enrichment.md — "Set a pet's breed".
-- Replace placeholders before running. No real PII in committed copies.

-- ---------------------------------------------------------------------------
-- 1) Find the pet (confirm pet_id)
-- ---------------------------------------------------------------------------
SELECT d.pet_id, d.name AS pet_name, o.name AS owner_name, d.breed_id, d.breed_secondary_id
FROM pet d
JOIN owner o ON o.owner_id = d.owner_id
WHERE d.pet_id = 123;   -- <-- placeholder pet_id

-- Optional: search by name if you forgot the id (may return multiple rows)
-- SELECT d.pet_id, d.name, o.name AS owner_name
-- FROM pet d
-- JOIN owner o ON o.owner_id = d.owner_id
-- WHERE d.name ILIKE '%PetName%';

-- ---------------------------------------------------------------------------
-- 2) Pick breed_id from catalog (or run lookup_breeds.sql)
-- ---------------------------------------------------------------------------
-- SELECT breed_id, name_de, name_en FROM breed ORDER BY name_de;

-- ---------------------------------------------------------------------------
-- 3) UPDATE (primary breed required; secondary optional — comment out if unused)
-- ---------------------------------------------------------------------------
BEGIN;

UPDATE pet
SET
  breed_id = 1,              -- <-- placeholder breed_id from breed table
  breed_secondary_id = NULL  -- or e.g. 2 for a mix; keep NULL if purebred / unknown
WHERE pet_id = 123;          -- <-- same pet_id as step 1

-- ---------------------------------------------------------------------------
-- 4) Verify (names via JOIN — still stored as ids on pet)
-- ---------------------------------------------------------------------------
SELECT
  d.pet_id,
  d.name AS pet_name,
  d.breed_id,
  b.name_de AS breed_de,
  d.breed_secondary_id,
  b2.name_de AS breed_secondary_de
FROM pet d
LEFT JOIN breed b ON b.breed_id = d.breed_id
LEFT JOIN breed b2 ON b2.breed_id = d.breed_secondary_id
WHERE d.pet_id = 123;

COMMIT;
-- If something looks wrong before COMMIT: ROLLBACK;
