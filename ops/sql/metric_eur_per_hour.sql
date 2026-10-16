-- Effective €/hour by condition × shaved_down (#27 / #170).
-- Definition: docs/runbooks/analytics.md — metric_eur_per_hour(p_start, p_end).
-- Rates are NULL when n < MIN_N (metric_constants). Real results → docs/notes/ only.
--
-- Run (encoding-safe — never pipe SQL text through PowerShell):
--   docker compose cp .\ops\sql\metric_eur_per_hour.sql db:/tmp/q.sql
--   docker compose exec -T db psql -U muttmetrics -d muttmetrics -f /tmp/q.sql
--
-- Edit the inclusive date range (week example = Monday … Sunday).

SELECT
    condition_score,
    shaved_down,
    n,
    groomed_minutes,
    hours,
    revenue_ex_tip,
    revenue_inc_tip,
    eur_per_hour_ex_tip,
    eur_per_hour_inc_tip
FROM metric_eur_per_hour(DATE '2026-03-02', DATE '2026-03-08')
ORDER BY condition_score, shaved_down;
