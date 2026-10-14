# Ops: analytics metrics (glossary)

Written definitions for M5 **First Real Numbers** ([#126](https://github.com/BOYSABIO/muttmetrics/issues/126); path [#159](https://github.com/BOYSABIO/muttmetrics/issues/159)).

This runbook is the **contract**. Views ([#155](https://github.com/BOYSABIO/muttmetrics/issues/155)), metric recipes ([#27](https://github.com/BOYSABIO/muttmetrics/issues/27)–[#29](https://github.com/BOYSABIO/muttmetrics/issues/29)), the API ([#156](https://github.com/BOYSABIO/muttmetrics/issues/156)), and the dashboard ([#158](https://github.com/BOYSABIO/muttmetrics/issues/158)) **cite this file** — they do not restate formulas in their own words.

Until those views exist, “how to run” means: encoding-safe `psql` ([#154](https://github.com/BOYSABIO/muttmetrics/issues/154)) against whatever recipe/view the metric issue ships. Results that include real volume or money go to `docs/notes/` only.

## How to run

Prefer selecting from the metric **views** once [#155](https://github.com/BOYSABIO/muttmetrics/issues/155) lands. Until then, use the `ops/sql/` recipe named by each metric issue.

Encoding-safe (never pipe SQL text through PowerShell):

```powershell
docker compose cp .\ops\sql\<recipe>.sql db:/tmp/q.sql
docker compose exec -T db psql -U muttmetrics -d muttmetrics -f /tmp/q.sql
```

Or open the same SQL in the Postgres extension. See [`db-peek.md`](./db-peek.md) and [`ops/README.md`](../../ops/README.md).

## Privacy (public vs private)

Same pattern as [`compliance.md`](./compliance.md): **how** we measure is public; **what** the salon scored is private.

| Put here (git / public issues) | Put in `docs/notes/` (gitignored) |
|--------------------------------|-----------------------------------|
| Definitions, formulas, `MIN_N`, status rules | Weekly €/hour tables, utilization, pivot rates, any `n` tied to a real week |
| Qualitative notes with no volume (“habit still weak”) | Client / dog names, raw exports from production-like DBs |

Do **not** paste salon money or weekly metric tables into a public issue comment.

## Visit eligibility (shared)

Every M5 metric that aggregates visits uses this filter unless a glossary entry explicitly narrows further (e.g. overrun needs a stored prediction).

| Rule | Meaning |
|------|---------|
| **Include** | `visit.status` is `'completed'` **or** `NULL` (legacy rows before status was filled) |
| **Exclude** | `status` in (`'cancelled'`, `'no_show'`) — groom did not happen / should not count as a logged job |
| **Week** | Monday–Sunday on `visit.visit_date` (salon calendar), same as compliance |
| **Condition polarity** | `condition_score`: **0 = worst … 5 = best** ([#123](https://github.com/BOYSABIO/muttmetrics/issues/123)) |

This matches the compliance numerator so “completed visits this week” means the same thing in capture health and in analytics.

## Small-sample rule

**Constant:** `MIN_N = 5` (named once; views, API, and dashboard must use this name/value — no scattered literals).

### What is a “cell”?

A **cell** is one group produced by that metric’s **GROUP BY** — **not** “per dog” and **not** automatically “per calendar day.”

| Metric | Typical cell (group of visits) | What `n` counts |
|--------|--------------------------------|-----------------|
| €/hour (#27) | One (`condition_score`, `shaved_down`) bucket **within a calendar week** | Eligible visits in that bucket — **many dogs** can sit in the same cell |
| Pivot / overrun / P90 miss (#28) | One week (dashboard), plus an overall / all-time view for ops | Eligible visits in that slice |
| Utilization (#29) | One `visit_date` | Visits that day |

**Why week, not month, for rates:** the salon can change pricing, mix, and habit in a few days. A week matches that pulse and the “This week” dashboard (#158). A month averages those turns away. Month (or any longer rollup) is a later query on the same rows when you want a smoother trend — not the primary grain.

So `MIN_N` is “enough visits **in this bucket** to show a mean/rate,” not “this dog has had 5 appointments.”

### When the rule applies

| Kind of number | Rule |
|----------------|------|
| **Averages and rates** (€/hour, pivot rate, avg overrun, P90 miss rate) | If `n < MIN_N`, **hide** the average/rate; show `n` + **“not enough grooms yet”** |
| **Day totals** (utilization: sum of planned / actual minutes) | Still **show the sums** for that day (they are facts, not a dressed-up mean). Always show `n`. Optionally mark the day as thin if `n < MIN_N`, but do not blank out “120 actual minutes.” |

`n` is always visible on every cell. A small `n` is not “a slightly worse estimate” — for averages it is a different kind of statement (anecdote).

**Why `MIN_N = 5`:** With 1–2 visits a rate cell is one story; with 3–4 one outlier still owns the mean. Five is the product floor for a one-groomer salon early on. A quiet Tuesday with 2 dogs can still show utilization **totals**; we just will not pretend a 2-visit €/hour cell is a KPI. Change the number only by amending this runbook and the single code constant — not per screen.

## Glossary

### Effective €/hour

**Question:** For eligible visits, what did we earn per hour of groom time, sliced by coat condition × whether we shaved down?

We publish **two** named rates so pricing power and take-home are never confused (see learning note below).

| Piece | Definition |
|-------|------------|
| **Eligible visits** | Shared eligibility, **and** `final_price IS NOT NULL`, **and** `actual_minutes IS NOT NULL`, **and** `actual_minutes > 0` |
| **Hours** | `actual_minutes / 60.0` |
| **Revenue (ex tip)** | `final_price` |
| **Revenue (inc tip)** | `final_price + coalesce(tip, 0)` — missing tip counts as `0`, not “unknown revenue” |
| **€/hour ex tip** | `sum(revenue ex tip) / sum(hours)` over the cell |
| **€/hour inc tip** | `sum(revenue inc tip) / sum(hours)` over the cell |
| **Grouping** | Week × `condition_score` × `shaved_down` (week = Mon–Sun on `visit_date`) |
| **Unit** | Euro per hour |
| **`n`** | Count of eligible visits in the cell; apply `MIN_N` |
| **NULL price / NULL minutes** | Visit **excluded** from this metric (not treated as €0 or 0 minutes) |

**Dashboard default (#158):** lead with **€/hour inc tip** (what the groomer took home). Always offer or show **ex tip** beside it (or in a secondary line) so goodwill tips cannot hide weak list pricing.

**ML / analysis default:** prefer **ex tip** (and tip as its own outcome or feature) so models do not treat generosity as “this condition pays well.”

### Overrun vs P50

| Piece | Definition |
|-------|------------|
| **Eligible** | Shared eligibility, **and** `predicted_min_p50 IS NOT NULL`, **and** `actual_minutes IS NOT NULL` |
| **Overrun (minutes)** | `actual_minutes - predicted_min_p50` |
| **Sign** | **Positive** → job ran longer than P50 (under-predicted). **Negative** → finished under P50 |
| **Cell average** | `avg(overrun)` with `n`; apply `MIN_N` |
| **No prediction** | Visit **excluded** from overrun (stated; do not invent a prior at read time) |

### P90 miss

| Piece | Definition |
|-------|------------|
| **Eligible** | Shared eligibility, **and** `predicted_min_p90 IS NOT NULL`, **and** `actual_minutes IS NOT NULL` |
| **Miss** | `actual_minutes > predicted_min_p90` (boolean) |
| **P90 miss rate** | `count(miss) / n` on eligible visits; apply `MIN_N` |
| **No prediction** | **Excluded** (same as overrun) |

### Pivot rate

| Piece | Definition |
|-------|------------|
| **Eligible** | Shared eligibility only (prediction not required) |
| **Pivot** | `pivoted IS TRUE` |
| **Pivot rate** | `count(pivoted is true) / n`; `NULL`/`false` count as not pivoted for the numerator; apply `MIN_N` |
| **Note** | Visits without a stored prediction **still count** here (unlike overrun) |

**Executable views (#28):** `metric_pivot_rate`, `metric_overrun`, `metric_p90_miss` (weekly rows + `week_start IS NULL` overall). Ops peek: [`ops/sql/metric_prediction_health.sql`](../../ops/sql/metric_prediction_health.sql). Capture UI still sets booked = actual until groomer calendar booking exists ([#44](https://github.com/BOYSABIO/muttmetrics/issues/44)); multi-session jobs are [#165](https://github.com/BOYSABIO/muttmetrics/issues/165).

### Utilization per day

| Piece | Definition |
|-------|------------|
| **Grain** | One row per `visit_date` (eligible visits that day) |
| **Planned minutes** | `sum(predicted_min_p50)` over visits that have P50 — **not** booking-system “booked” minutes (there is no booking product yet) |
| **Planned worst case** | `sum(predicted_min_p90)` where P90 is present |
| **Actual minutes** | `sum(actual_minutes)` where present |
| **Closing buffer** | Parameter `buffer_minutes` (e.g. minutes available before close) — **not** a hardcoded literal in the view; exposed as a SQL function argument ([#155](https://github.com/BOYSABIO/muttmetrics/issues/155) / [#29](https://github.com/BOYSABIO/muttmetrics/issues/29)) |
| **Over buffer** | e.g. planned worst case (or chosen planned measure) **>** `buffer_minutes` — exact flag defined when the function ships; must match the fixture |
| **Missing predictions** | Count and surface those visits; **do not** treat missing P50 as 0 planned minutes |

**Executable (#29):** `SELECT * FROM metric_utilization(240)` — function, not a view. Ops: [`ops/sql/metric_utilization.sql`](../../ops/sql/metric_utilization.sql). `over_buffer` = `planned_p90 > buffer_minutes`.

## Named constants

| Name | Value | Used by |
|------|-------|---------|
| `MIN_N` | `5` | Metric views, `GET /metrics/week`, “This week” UI — one definition |

When code lands, this value should appear **once** (e.g. a SQL constant table, a migration-seeded setting, or a single module constant imported by API and tests). Amending the number means amending this table and that single implementation site.

## Scope of M5 (what is in vs out)

**In the product path (#159):** exactly the glossary entries above — €/hour (#27), pivot / overrun / P90 miss (#28), utilization (#29) — plus capture health in [`compliance.md`](./compliance.md). That is the “This week” screen.

**Not in M5 (on purpose):** total revenue, tip totals, client counts, breed mixes, month rollups, P&L. Those are one `SUM` / `GROUP BY` away once visits are logged. Adding them to the dashboard before the three decision metrics ship just dilutes the screen. When something new earns a permanent definition (numerator, denominator, eligibility, `MIN_N`), amend **this** runbook first — same rule as #126.

## Learning notes

**Tips vs list price.** Restaurants often separate “sales” (house) from tips (staff). A sole groomer *is* the house — take-home includes tips. For analytics and future models, tip-inflated €/hour can hide weak pricing (“clients tip when they feel guilty about mats”). Defining **both** rates keeps the groomer payoff honest and the analyst lens clean.

**Operational definition.** If SQL, API, and UI disagree on revenue, none of them is “the metric.” This file is the contract.

**Small `n`.** Hiding the average is a feature. Showing a precise €/hour on two visits trains the wrong trust.

## Related

- Path / exit: [#159](https://github.com/BOYSABIO/muttmetrics/issues/159)
- Views: [#155](https://github.com/BOYSABIO/muttmetrics/issues/155) · fixtures: [#16](https://github.com/BOYSABIO/muttmetrics/issues/16)
- Metrics: [#27](https://github.com/BOYSABIO/muttmetrics/issues/27) €/hour · [#28](https://github.com/BOYSABIO/muttmetrics/issues/28) pivot/overrun · [#29](https://github.com/BOYSABIO/muttmetrics/issues/29) utilization
- Capture health: [`compliance.md`](./compliance.md) · priors/calibration: [`prior.md`](../prior.md)
- Encoding-safe SQL: [#154](https://github.com/BOYSABIO/muttmetrics/issues/154)
