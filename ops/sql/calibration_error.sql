-- Predicted vs actual duration error (#25), reconciled with #28 views (ADR-003).
--
-- Groomer-facing totals live in metric_overrun / metric_p90_miss
-- (docs/runbooks/analytics.md). Breed / condition slices below keep the SAME
-- eligibility and overrun formula (actual - P50; P90 hit = actual <= P90).
-- They are not a second definition — only a different GROUP BY.
--
-- Run (encoding-safe — never pipe SQL text through PowerShell):
--   docker compose cp .\ops\sql\calibration_error.sql db:/tmp/q.sql
--   docker compose exec -T db psql -U muttmetrics -d muttmetrics -f /tmp/q.sql

-- ---------------------------------------------------------------------------
-- 0) Single source check — overall rows from the metric views (#28)
--    avg_overrun_minutes ≡ avg_error_p50; miss_rate ≡ 1 - p90_hit_rate
--    (when both use the same prediction filters; views require P50 or P90 alone)
-- ---------------------------------------------------------------------------
SELECT
  o.n AS overrun_n,
  ROUND(o.avg_overrun_minutes, 1) AS avg_overrun_minutes,
  p.n AS p90_n,
  p.miss_count,
  ROUND(p.miss_rate, 2) AS miss_rate,
  ROUND(1.0 - p.miss_rate, 2) AS p90_hit_rate
FROM metric_overrun o
CROSS JOIN metric_p90_miss p
WHERE o.week_start IS NULL
  AND p.week_start IS NULL;

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
-- 3) Overall from visits (same filters as historical recipe)
--     Prefer section 0 for the ADR-003 view numbers; this block is the
--     breed-calibration twin when both P50 and P90 are required.
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
