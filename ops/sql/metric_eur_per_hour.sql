-- Effective €/hour by condition × shaved_down (#27).
-- Definition: docs/runbooks/analytics.md — read from view metric_eur_per_hour (ADR-003).
-- Rates are NULL when n < MIN_N (5). Real results → docs/notes/ only, never issue comments.
--
-- Run (encoding-safe — never pipe SQL text through PowerShell):
--   docker compose cp .\ops\sql\metric_eur_per_hour.sql db:/tmp/q.sql
--   docker compose exec -T db psql -U muttmetrics -d muttmetrics -f /tmp/q.sql
--
-- Edit week_start to the Monday of the week you care about.

SELECT
    week_start,
    condition_score,
    shaved_down,
    n,
    groomed_minutes,
    hours,
    revenue_ex_tip,
    revenue_inc_tip,
    eur_per_hour_ex_tip,
    eur_per_hour_inc_tip
FROM metric_eur_per_hour
WHERE week_start = DATE '2026-03-02'  -- Syn* fixture week; change for real peeks
ORDER BY condition_score, shaved_down;
