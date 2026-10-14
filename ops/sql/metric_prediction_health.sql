-- Pivot rate + overrun vs P50 + P90 miss (#28).
-- Definitions: docs/runbooks/analytics.md — read from views (ADR-003).
-- Rates / averages are NULL when n < MIN_N (5).
-- Real salon numbers → docs/notes/ only, never issue comments.
--
-- Run (encoding-safe — never pipe SQL text through PowerShell):
--   docker compose cp .\ops\sql\metric_prediction_health.sql db:/tmp/q.sql
--   docker compose exec -T db psql -U muttmetrics -d muttmetrics -f /tmp/q.sql
--
-- Edit week_start (Monday) for a weekly peek; overall rows have week_start IS NULL.
-- Synthetic fixture week example: 2026-03-02.

-- ---------------------------------------------------------------------------
-- 1) One week (edit the date)
-- ---------------------------------------------------------------------------
SELECT 'pivot' AS metric, week_start, n, pivoted_count AS detail, pivot_rate AS value
FROM metric_pivot_rate
WHERE week_start = DATE '2026-03-02'
UNION ALL
SELECT 'overrun', week_start, n, NULL, avg_overrun_minutes
FROM metric_overrun
WHERE week_start = DATE '2026-03-02'
UNION ALL
SELECT 'p90_miss', week_start, n, miss_count, miss_rate
FROM metric_p90_miss
WHERE week_start = DATE '2026-03-02';

-- ---------------------------------------------------------------------------
-- 2) Overall (all eligible history) — week_start IS NULL
-- ---------------------------------------------------------------------------
SELECT 'pivot' AS metric, week_start, n, pivoted_count AS detail, pivot_rate AS value
FROM metric_pivot_rate
WHERE week_start IS NULL
UNION ALL
SELECT 'overrun', week_start, n, NULL, avg_overrun_minutes
FROM metric_overrun
WHERE week_start IS NULL
UNION ALL
SELECT 'p90_miss', week_start, n, miss_count, miss_rate
FROM metric_p90_miss
WHERE week_start IS NULL;

-- ---------------------------------------------------------------------------
-- 3) Optional CSV-shaped export (synthetic-friendly column list)
--    In psql: \copy ( ... ) TO 'docs/notes/prediction_health.csv' CSV HEADER
--    Never commit real exports.
-- ---------------------------------------------------------------------------
-- SELECT week_start, n, pivoted_count, pivot_rate
-- FROM metric_pivot_rate
-- ORDER BY week_start NULLS LAST;
