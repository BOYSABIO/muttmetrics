-- Local hygiene: remove synthetic clients created by pytest / capture experiments.
-- KEEP real salon rows (e.g. Thomas / Milla). Review the PREVIEW section before DELETE.
--
-- Run against local compose Postgres only — never production.
--
-- Examples:
--   docker compose exec -T db psql -U muttmetrics -d muttmetrics -f - < scripts/cleanup_synthetic_clients.sql
--   Or paste into the Postgres extension / pgAdmin connected to muttmetrics.
--   Get-Content .\scripts\cleanup_synthetic_clients.sql -Raw | docker compose exec -T db psql -U muttmetrics -d muttmetrics

BEGIN;

-- ---------------------------------------------------------------------------
-- PREVIEW: owners / dogs that would be removed
-- ---------------------------------------------------------------------------
SELECT o.owner_id, o.name AS owner_name, d.dog_id, d.name AS dog_name
FROM owner o
LEFT JOIN dog d ON d.owner_id = o.owner_id
WHERE o.name ILIKE 'Dog Lesson Owner%'
   OR o.name ILIKE 'Lesson %Owner%'          -- e.g. "Lesson Two Owner ba6671e9"
   OR o.name ILIKE 'Capture Owner%'
   OR o.name ILIKE 'Flow Owner%'
   OR o.name ILIKE 'Test Owner%'
   OR o.name IN ('NEW OWNER TEST', 'THE NEW OWNER')
   OR d.name ILIKE 'BrowseDog%'
   OR d.name ILIKE 'Capture Dog%'
   OR d.name ILIKE 'Flow Dog%'
   OR d.name ILIKE 'Test Dog%'
   OR d.name IN ('NEW DOG TEST', 'THE NEW DOG')
   -- pytest Bella / unique-token dogs (hex suffix); does NOT match plain 'Milla'
   OR d.name ~* '^Bella[ 0-9a-f]{4,}$'
ORDER BY o.name, d.name;

-- ---------------------------------------------------------------------------
-- DELETE (FK order: visit → dog → owner)
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE doomed_owner ON COMMIT DROP AS
SELECT DISTINCT o.owner_id
FROM owner o
LEFT JOIN dog d ON d.owner_id = o.owner_id
WHERE o.name ILIKE 'Dog Lesson Owner%'
   OR o.name ILIKE 'Lesson %Owner%'
   OR o.name ILIKE 'Capture Owner%'
   OR o.name ILIKE 'Flow Owner%'
   OR o.name ILIKE 'Test Owner%'
   OR o.name IN ('NEW OWNER TEST', 'THE NEW OWNER')
   OR d.name ILIKE 'BrowseDog%'
   OR d.name ILIKE 'Capture Dog%'
   OR d.name ILIKE 'Flow Dog%'
   OR d.name ILIKE 'Test Dog%'
   OR d.name IN ('NEW DOG TEST', 'THE NEW DOG')
   OR d.name ~* '^Bella[ 0-9a-f]{4,}$';

-- Safety: never doom Thomas (case-insensitive exact-ish match on common real owner)
DELETE FROM doomed_owner
WHERE owner_id IN (
  SELECT owner_id FROM owner WHERE lower(trim(name)) = 'thomas'
);

DELETE FROM visit
WHERE owner_id IN (SELECT owner_id FROM doomed_owner)
   OR dog_id IN (
     SELECT dog_id FROM dog WHERE owner_id IN (SELECT owner_id FROM doomed_owner)
   );

DELETE FROM dog
WHERE owner_id IN (SELECT owner_id FROM doomed_owner);

DELETE FROM owner
WHERE owner_id IN (SELECT owner_id FROM doomed_owner);

-- ---------------------------------------------------------------------------
-- REMAINING clients (expect Thomas / Milla here)
-- ---------------------------------------------------------------------------
SELECT o.owner_id, o.name AS owner_name, d.dog_id, d.name AS dog_name
FROM owner o
LEFT JOIN dog d ON d.owner_id = o.owner_id
ORDER BY o.name, d.name;

COMMIT;
