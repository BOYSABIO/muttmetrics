-- Utilization per day vs closing buffer (#29).
-- Definition: docs/runbooks/analytics.md — SQL function metric_utilization(buffer_minutes)
-- (ADR-003: parameter → function, not a view). Real results → docs/notes/ only.
--
-- Run (encoding-safe — never pipe SQL text through PowerShell):
--   docker compose cp .\ops\sql\metric_utilization.sql db:/tmp/q.sql
--   docker compose exec -T db psql -U muttmetrics -d muttmetrics -f /tmp/q.sql
--
-- Edit the buffer (minutes available before close). Fixture uses 240.

SELECT *
FROM metric_utilization(240)
ORDER BY visit_date;
