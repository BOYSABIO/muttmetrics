-- Recipe: set dog.breed_id (and optional breed_secondary_id).
-- See docs/ops-enrichment.md — "Set a dog's breed".
-- Replace placeholders before running. No real PII in committed copies.

-- ---------------------------------------------------------------------------
-- 1) Find the dog (confirm dog_id)
-- ---------------------------------------------------------------------------
SELECT d.dog_id, d.name AS dog_name, o.name AS owner_name, d.breed_id, d.breed_secondary_id
FROM dog d
JOIN owner o ON o.owner_id = d.owner_id
WHERE d.dog_id = 123;   -- <-- placeholder dog_id

-- Optional: search by name if you forgot the id (may return multiple rows)
-- SELECT d.dog_id, d.name, o.name AS owner_name
-- FROM dog d
-- JOIN owner o ON o.owner_id = d.owner_id
-- WHERE d.name ILIKE '%Milla%';

-- ---------------------------------------------------------------------------
-- 2) Pick breed_id from catalog (or run lookup_breeds.sql)
-- ---------------------------------------------------------------------------
-- SELECT breed_id, name_de, name_en FROM breed ORDER BY name_de;

-- ---------------------------------------------------------------------------
-- 3) UPDATE (primary breed required; secondary optional — comment out if unused)
-- ---------------------------------------------------------------------------
BEGIN;

UPDATE dog
SET
  breed_id = 1,              -- <-- placeholder breed_id from breed table
  breed_secondary_id = NULL  -- or e.g. 2 for a mix; keep NULL if purebred / unknown
WHERE dog_id = 123;          -- <-- same dog_id as step 1

-- ---------------------------------------------------------------------------
-- 4) Verify (names via JOIN — still stored as ids on dog)
-- ---------------------------------------------------------------------------
SELECT
  d.dog_id,
  d.name AS dog_name,
  d.breed_id,
  b.name_de AS breed_de,
  d.breed_secondary_id,
  b2.name_de AS breed_secondary_de
FROM dog d
LEFT JOIN breed b ON b.breed_id = d.breed_id
LEFT JOIN breed b2 ON b2.breed_id = d.breed_secondary_id
WHERE d.dog_id = 123;

COMMIT;
-- If something looks wrong before COMMIT: ROLLBACK;
