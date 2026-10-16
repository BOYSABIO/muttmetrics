-- Utilization per day vs closing buffer (#29 / #170).
-- Definition: docs/runbooks/analytics.md —
--   metric_utilization(buffer_minutes, p_start, p_end)
-- Real results → docs/notes/ only.
--
-- Run (encoding-safe — never pipe SQL text through PowerShell):
--   docker compose cp .\ops\sql\metric_utilization.sql db:/tmp/q.sql
--   docker compose exec -T db psql -U muttmetrics -d muttmetrics -f /tmp/q.sql
--
-- Edit buffer and inclusive date range. Fixture week uses 240 + Syn* week.

SELECT *
FROM metric_utilization(240, DATE '2026-03-02', DATE '2026-03-08')
ORDER BY visit_date;
