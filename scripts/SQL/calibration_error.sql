-- Predicted vs actual duration error (#25).
-- Only completed (or legacy NULL status) visits that have a P50 stored.
--
-- Run:
--   Get-Content .\scripts\SQL\calibration_error.sql -Raw |
--     docker compose exec -T db psql -U muttmetrics -d muttmetrics

-- ---------------------------------------------------------------------------
-- 1) By breed — “are we systematically underestimating Doodles?”
-- ---------------------------------------------------------------------------
-- error_p50 > 0  → actual longer than P50 (under-predicted)
-- error_p50 < 0  → actual shorter than P50 (over-predicted)
-- p90_hit_rate   → share of visits where actual <= P90 (aim ~0.9 when n is large)

SELECT
  COALESCE(b.name_en, '(no breed)') AS breed,
  COUNT(*) AS n,
  ROUND(AVG(v.actual_minutes - v.predicted_min_p50)::numeric, 1) AS avg_error_p50,
  ROUND(AVG(v.actual_minutes - v.predicted_min_p90)::numeric, 1) AS avg_error_p90,
  ROUND(
    AVG(
      CASE WHEN v.actual_minutes <= v.predicted_min_p90 THEN 1.0 ELSE 0.0 END
    )::numeric,
    2
  ) AS p90_hit_rate
FROM visit v
LEFT JOIN dog d ON d.dog_id = v.dog_id
LEFT JOIN breed b ON b.breed_id = d.breed_id
WHERE v.actual_minutes IS NOT NULL
  AND v.predicted_min_p50 IS NOT NULL
  AND v.predicted_min_p90 IS NOT NULL
  AND (v.status IS NULL OR v.status = 'completed')
GROUP BY b.name_en
ORDER BY n DESC, breed;

-- ---------------------------------------------------------------------------
-- 2) By condition_score — coat condition vs error
-- ---------------------------------------------------------------------------
SELECT
  v.condition_score,
  COUNT(*) AS n,
  ROUND(AVG(v.actual_minutes - v.predicted_min_p50)::numeric, 1) AS avg_error_p50,
  ROUND(
    AVG(
      CASE WHEN v.actual_minutes <= v.predicted_min_p90 THEN 1.0 ELSE 0.0 END
    )::numeric,
    2
  ) AS p90_hit_rate
FROM visit v
WHERE v.actual_minutes IS NOT NULL
  AND v.predicted_min_p50 IS NOT NULL
  AND v.predicted_min_p90 IS NOT NULL
  AND (v.status IS NULL OR v.status = 'completed')
GROUP BY v.condition_score
ORDER BY v.condition_score NULLS LAST;

-- ---------------------------------------------------------------------------
-- 3) Overall (one row) — weekly sanity check
-- ---------------------------------------------------------------------------
SELECT
  COUNT(*) AS n,
  ROUND(AVG(v.actual_minutes - v.predicted_min_p50)::numeric, 1) AS avg_error_p50,
  ROUND(
    AVG(
      CASE WHEN v.actual_minutes <= v.predicted_min_p90 THEN 1.0 ELSE 0.0 END
    )::numeric,
    2
  ) AS p90_hit_rate
FROM visit v
WHERE v.actual_minutes IS NOT NULL
  AND v.predicted_min_p50 IS NOT NULL
  AND v.predicted_min_p90 IS NOT NULL
  AND (v.status IS NULL OR v.status = 'completed');