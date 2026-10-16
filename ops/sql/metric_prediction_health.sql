-- Pivot rate + overrun vs P50 + P90 miss (#28 / #170).
-- Definitions: docs/runbooks/analytics.md — range functions (ADR-003).
-- Rates / averages are NULL when n < MIN_N (metric_constants).
-- Real salon numbers → docs/notes/ only, never issue comments.
--
-- Run (encoding-safe — never pipe SQL text through PowerShell):
--   docker compose cp .\ops\sql\metric_prediction_health.sql db:/tmp/q.sql
--   docker compose exec -T db psql -U muttmetrics -d muttmetrics -f /tmp/q.sql
--
-- Edit the inclusive range. Week example: Mon 2026-03-02 … Sun 2026-03-08.
-- "Overall" = a very wide range (not a NULL week_start row anymore).

-- ---------------------------------------------------------------------------
-- 1) One week (edit the dates)
-- ---------------------------------------------------------------------------
SELECT 'pivot' AS metric, n, pivoted_count AS detail, pivot_rate AS value
FROM metric_pivot_rate(DATE '2026-03-02', DATE '2026-03-08')
UNION ALL
SELECT 'overrun', n, NULL, avg_overrun_minutes
FROM metric_overrun(DATE '2026-03-02', DATE '2026-03-08')
UNION ALL
SELECT 'p90_miss', n, miss_count, miss_rate
FROM metric_p90_miss(DATE '2026-03-02', DATE '2026-03-08');

-- ---------------------------------------------------------------------------
-- 2) Wide range ≈ overall history
-- ---------------------------------------------------------------------------
SELECT 'pivot' AS metric, n, pivoted_count AS detail, pivot_rate AS value
FROM metric_pivot_rate(DATE '1900-01-01', DATE '9999-12-31')
UNION ALL
SELECT 'overrun', n, NULL, avg_overrun_minutes
FROM metric_overrun(DATE '1900-01-01', DATE '9999-12-31')
UNION ALL
SELECT 'p90_miss', n, miss_count, miss_rate
FROM metric_p90_miss(DATE '1900-01-01', DATE '9999-12-31');
