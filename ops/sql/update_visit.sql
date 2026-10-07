-- Recipe: fix / enrich a visit row (event facts only).
-- See docs/runbooks/enrichment.md ΓÇö "Fix / enrich a visit".
-- Do NOT set days_since_last or predicted_min_*.
-- Photos live in the photo table (API upload / photo_purge) ΓÇö not on visit.

-- ---------------------------------------------------------------------------
-- 1) Inspect
-- ---------------------------------------------------------------------------
SELECT
  v.visit_id,
  v.visit_date,
  v.actual_minutes,
  v.condition_score,
  v.what_surprised_me,
  v.status,
  v.actual_service_id,
  v.final_price,
  v.tip,
  d.name AS dog_name,
  o.name AS owner_name
FROM visit v
JOIN dog d ON d.dog_id = v.dog_id
JOIN owner o ON o.owner_id = v.owner_id
WHERE v.visit_id = 123;   -- <-- placeholder visit_id

-- ---------------------------------------------------------------------------
-- 2) UPDATE ΓÇö edit only the columns you need; comment out the rest
-- ---------------------------------------------------------------------------
BEGIN;

UPDATE visit
SET
  visit_date = DATE '2026-09-17',           -- <-- or leave unchanged / comment out
  actual_minutes = 90,                      -- <-- wall-clock minutes (> 0)
  condition_score = 3,                      -- <-- 0ΓÇô5 or NULL
  what_surprised_me = 'Example note only',  -- <-- placeholder text
  status = 'completed',                     -- completed | cancelled | no_show
  actual_service_id = 4,                    -- <-- optional; from service catalog
  final_price = 75.00,                      -- <-- optional
  tip = 10.00                               -- <-- optional
WHERE visit_id = 123;

-- ---------------------------------------------------------------------------
-- 3) Verify
-- ---------------------------------------------------------------------------
SELECT visit_id, visit_date, actual_minutes, condition_score, what_surprised_me,
       status, actual_service_id, final_price, tip
FROM visit
WHERE visit_id = 123;

COMMIT;
