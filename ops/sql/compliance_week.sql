-- Weekly capture compliance numerator (#22).
-- Denominator is manual: ask how many dogs were groomed that week.
-- Compliance % = 100.0 * completed_visits / grooms_reported  (skip if denom = 0).
--
-- Week = MonΓÇôSun on visit_date (salon calendar). Edit the two dates below.
-- Example first formal week: 2026-10-06 .. 2026-10-12
--
-- Run in the Postgres extension, or:
--   Get-Content .\ops\sql\compliance_week.sql -Raw |
--     docker compose exec -T db psql -U muttmetrics -d muttmetrics

-- ---------------------------------------------------------------------------
-- 0) Set the week (edit these)
-- ---------------------------------------------------------------------------
-- Tip: keep them as literals in each query below, or use a single session:
--   \set week_start '\'2026-10-06\''
--   \set week_end   '\'2026-10-12\''
-- psql variables are optional; plain dates are fine for the extension.

-- ---------------------------------------------------------------------------
-- 1) Numerator: completed visits in the week
-- ---------------------------------------------------------------------------
-- Count status = 'completed', and NULL (legacy rows before status was filled).
-- Exclude cancelled / no_show ΓÇö those are not "groom happened + should log".
SELECT COUNT(*) AS completed_visits
FROM visit
WHERE visit_date >= DATE '2026-10-06'
  AND visit_date <= DATE '2026-10-12'
  AND (status IS NULL OR status = 'completed');

-- ---------------------------------------------------------------------------
-- 2) List (sanity check ΓÇö wrong dates / doubles show up here)
-- ---------------------------------------------------------------------------
SELECT
  v.visit_id,
  v.visit_date,
  v.actual_minutes,
  v.status,
  d.name AS dog_name,
  o.name AS owner_name
FROM visit v
JOIN dog d ON d.dog_id = v.dog_id
JOIN owner o ON o.owner_id = v.owner_id
WHERE v.visit_date >= DATE '2026-10-06'
  AND v.visit_date <= DATE '2026-10-12'
  AND (v.status IS NULL OR v.status = 'completed')
ORDER BY v.visit_date, v.visit_id;

-- ---------------------------------------------------------------------------
-- 3) Scratch pad (do the % yourself)
-- ---------------------------------------------------------------------------
-- grooms_reported = ___
-- completed_visits (query 1)  = ___
-- compliance % = 100 * completed_visits / grooms_reported = ___
