# Ops: analytics metrics (glossary)

Written definitions for M5 **First Real Numbers** ([#126](https://github.com/BOYSABIO/muttmetrics/issues/126); path [#159](https://github.com/BOYSABIO/muttmetrics/issues/159)).

This runbook is the **contract**. Range functions ([ADR-003](../architecture/adr/003-metric-views.md), [#170](https://github.com/BOYSABIO/muttmetrics/issues/170)), metric recipes ([#27](https://github.com/BOYSABIO/muttmetrics/issues/27)–[#29](https://github.com/BOYSABIO/muttmetrics/issues/29)), the API ([#156](https://github.com/BOYSABIO/muttmetrics/issues/156), [#170](https://github.com/BOYSABIO/muttmetrics/issues/170)), and the dashboard ([#158](https://github.com/BOYSABIO/muttmetrics/issues/158)) **cite this file** — they do not restate formulas in their own words.

Results that include real volume or money go to `docs/notes/` only.

## How to run

Every metric is a **range function** with inclusive dates. Same definition for a week, a month, or a custom window — only the arguments change.

| Metric | Call |
|--------|------|
| Summary (visits, minutes, revenue, overall €/hour) | `metric_summary(p_start, p_end)` |
| €/hour by coat condition (shave-downs one row) | `metric_eur_per_hour(p_start, p_end)` |
| Pivot / overrun / P90 miss | `metric_pivot_rate` / `metric_overrun` / `metric_p90_miss` `(p_start, p_end)` |
| Utilization per day | `metric_utilization(buffer_minutes, p_start, p_end)` |
| Utilization per week (month view) | `metric_utilization_weeks(buffer_minutes, p_start, p_end)`, built on the per-day function |

**Week** = Monday … Sunday (`p_end = p_start + 6`). **Month** = 1st … last day of that calendar month. **Overall history** ≈ a very wide range (ops recipes use `1900-01-01` … `9999-12-31`).

Encoding-safe (never pipe SQL text through PowerShell):

```powershell
docker compose cp .\ops\sql\<recipe>.sql db:/tmp/q.sql
docker compose exec -T db psql -U muttmetrics -d muttmetrics -f /tmp/q.sql
```

Or open the same SQL in the Postgres extension. See [`db-peek.md`](./db-peek.md) and [`ops/README.md`](../../ops/README.md).

API: `GET /metrics/period?start=&end=` (any inclusive range, max 366 days; response bounds are `start` / `end` — [#187](https://github.com/BOYSABIO/muttmetrics/issues/187)). Besides the range itself it returns `previous_period` (clipped to the same elapsed days while the range is still running: `previous_is_partial`), `recent` (the same block for the last `RECENT_DAYS` up to the range end or today) and `all_time` (totals since the first completed visit) — [#228](https://github.com/BOYSABIO/muttmetrics/issues/228). `GET /metrics/week?start=` (Monday) remains a thin Mon–Sun wrapper with `previous_week` for curls/ops.

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
| **Range** | Inclusive `visit.visit_date` between `p_start` and `p_end` (week = Mon–Sun; month = calendar month) |
| **Condition polarity** | `condition_score`: **0 = worst … 5 = best** ([#123](https://github.com/BOYSABIO/muttmetrics/issues/123)). On screen as words, one per score (2026-11-14): 0 *Matted*, 1 *Rough*, 2 *Tangled*, 3 *OK*, 4 *Good*, 5 *Great* (`frontend/src/condition.ts`; the stored value stays the number) |

This matches the compliance numerator so “completed visits” means the same thing in capture health and in analytics.

## Small-sample rule

**Constant:** `MIN_N = 5` (named once in `metric_constants`; SQL functions, API, and dashboard must use this name/value — no scattered literals).

### What is a “cell”?

A **cell** is one group produced by that metric’s **GROUP BY** — **not** “per dog” and **not** automatically “per calendar day.”

| Metric | Typical cell (group of visits) | What `n` counts |
|--------|--------------------------------|-----------------|
| €/hour (#27) | One coat condition (unshaved visits), or **all shave-downs together**, **within the chosen range** | Eligible visits in that bucket — **many dogs** can sit in the same cell |
| Pivot / overrun / P90 miss (#28) | The chosen range (week or month on the dashboard; wide range for ops “overall”) | Eligible visits in that slice |
| Utilization (#29) | One `visit_date` inside the range | Visits that day |

**Week vs month:** a week matches the salon’s short pulse (#158). A **month** (#170) is the same formulas on a longer range — useful early on when weekly cells sit under `MIN_N`. Do **not** average weekly averages to get a month; recompute from visit rows for that range.

**The recent window ([#228](https://github.com/BOYSABIO/muttmetrics/issues/228)):** some questions are slow. "Does this kind of coat pay less per hour?" spreads one period's grooms over up to 7 cells (6 conditions + shave-downs; 12 before 2026-11-14), so a week (or even a month) can't fill them. Those numbers use the **last `RECENT_DAYS` (90)** up to the end of the period being viewed (or today, if that's earlier): same functions, same `MIN_N`, a longer range. Ninety days fills the cells while old prices drop out within a quarter.

| Number on the This week screen | Range |
|---|---|
| Grooms, hours, take-home, overall €/hour | The selected week or month, compared with the previous one |
| Day by day (week) / week by week (month) | The selected period |
| €/hour by coat condition, the coat sentence | Last 90 days |
| Overrun, P90 miss (shown only once visits carry estimates) | Last 90 days |
| All time: the hero in **All** mode; in week and month only a one-line link to it (grooms so far, next milestone) | First completed visit → today |

**Comparisons:** while a period is still running, the previous one is clipped to the same number of elapsed days (Tuesday is compared with last Monday–Tuesday, not a whole week). A change is shown only when the previous period has grooms; a rate's change only when both rates passed `MIN_N`.

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

**Question:** For eligible visits, what did we earn per hour of groom time, sliced by the coat's condition on arrival, with shave-downs as their own group?

We publish **two** named rates so pricing power and take-home are never confused (see learning note below).

| Piece | Definition |
|-------|------------|
| **Eligible visits** | Shared eligibility, **and** `final_price IS NOT NULL`, **and** `actual_minutes IS NOT NULL`, **and** `actual_minutes > 0` |
| **Hours** | `actual_minutes / 60.0` |
| **Revenue (ex tip)** | `final_price` |
| **Revenue (inc tip)** | `final_price + coalesce(tip, 0)` — missing tip counts as `0`, not “unknown revenue” |
| **€/hour ex tip** | `sum(revenue ex tip) / sum(hours)` over the cell |
| **€/hour inc tip** | `sum(revenue inc tip) / sum(hours)` over the cell |
| **Grouping** | Range × (`condition_score` for unshaved visits **or** one shave-down cell). A visit with `shaved_down` true goes to the shave-down cell (`condition_score` NULL in the result) whatever its condition; otherwise it needs a `condition_score`. `shaved_down` NULL counts as not shaved. **Amended 2026-11-14** (migration `a7b8c9d0e1f2`): it was condition × shaved_down, up to 12 cells, and shave-downs (almost always bad coats) spread over cells that could never fill |
| **Unit** | Euro per hour |
| **`n`** | Count of eligible visits in the cell; apply `MIN_N` |
| **NULL price / NULL minutes** | Visit **excluded** from this metric (not treated as €0 or 0 minutes) |

**Dashboard default (#158):** lead with **€/hour inc tip** (what the groomer took home). Always offer or show **ex tip** beside it (or in a secondary line) so goodwill tips cannot hide weak list pricing.

**Period headline (not a condition cell):** overall €/hour for the selected range uses the same eligibility as above (priced + minutes > 0), without slicing by condition/shaved. Lives on `metric_summary(p_start, p_end)` (`eur_per_hour_n`, `eur_per_hour_ex_tip`, `eur_per_hour_inc_tip`) with `MIN_N` in SQL. The SPA must display those packaged fields — no frontend divide.

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

### Estimate bands (2026-11-14)

| Piece | Definition |
|-------|------------|
| **Eligible** | Shared eligibility, **and** `predicted_min_p50` **and** `predicted_min_p90` present, **and** `actual_minutes IS NOT NULL` (the P90-miss visits, minus any without a P50) |
| **Within P50** | `actual_minutes <= predicted_min_p50` ("within the typical time") |
| **Within P90** | `predicted_min_p50 < actual_minutes <= predicted_min_p90` ("longer, within the worst case") |
| **Past P90** | `actual_minutes > predicted_min_p90` (same as a P90 miss) |
| **`enough`** | `n >= MIN_N`. Counts are always facts; the screen draws the proportions only when `enough` |

**Executable:** `metric_estimate_bands(p_start, p_end)` → `n`, `within_p50`, `within_p90`, `past_p90`, `enough`. The three counts add up to `n`.

**On the screen (timing card, last 90 days):** one sentence judged against what a worst case is for: it should be beaten about **1 in 10** times. Past P90 above 15% → "estimates run short"; below 5% → "estimates are cautious"; otherwise "about right". Then the three bands as one bar, then the average overrun and the P90 miss rate.

### Pivot rate

| Piece | Definition |
|-------|------------|
| **Eligible** | Shared eligibility only (prediction not required) |
| **Pivot** | `pivoted IS TRUE` |
| **Pivot rate** | `count(pivoted is true) / n`; `NULL`/`false` count as not pivoted for the numerator; apply `MIN_N` |
| **Note** | Visits without a stored prediction **still count** here (unlike overrun) |

**Not captured yet (#178 / #188).** Nothing writes `visit.pivoted` today: capture sets booked = actual until booking exists ([#44](https://github.com/BOYSABIO/muttmetrics/issues/44)). Showing 0% would pretend we measured plan changes. Since 0.6.5 the screen has **no plan-changes row** at all ([#228](https://github.com/BOYSABIO/muttmetrics/issues/228)); it comes back with real data. **Decision ([#188](https://github.com/BOYSABIO/muttmetrics/issues/188), closed not planned):** no one-tap toggle before booking — package swaps are rare here, and capture is in-the-moment only. When #44 lands, derive `pivoted` at write time from `booked_service_id <> actual_service_id`; the SQL function needs no change.

**Executable (#28 / #170):** `metric_pivot_rate(p_start, p_end)`, `metric_overrun(…)`, `metric_p90_miss(…)`. Ops peek: [`ops/sql/metric_prediction_health.sql`](../../ops/sql/metric_prediction_health.sql). Capture UI still sets booked = actual until groomer calendar booking exists ([#44](https://github.com/BOYSABIO/muttmetrics/issues/44)); multi-session jobs are [#165](https://github.com/BOYSABIO/muttmetrics/issues/165).

### Utilization per day

| Piece | Definition |
|-------|------------|
| **Grain** | One row per `visit_date` (eligible visits that day) |
| **Planned minutes** | `sum(predicted_min_p50)` over visits that have P50 — **not** booking-system “booked” minutes (there is no booking product yet) |
| **Planned worst case** | `sum(predicted_min_p90)` where P90 is present |
| **Actual minutes** | `sum(actual_minutes)` where present |
| **Closing buffer** | Parameter `buffer_minutes` (e.g. minutes available before close) — **not** a hardcoded literal; it is the function's first argument ([#155](https://github.com/BOYSABIO/muttmetrics/issues/155) / [#29](https://github.com/BOYSABIO/muttmetrics/issues/29)) |
| **Over buffer** | `planned_p90 > buffer_minutes` (the planned worst case for the day exceeds the buffer); pinned by the fixture |
| **Missing predictions** | Count and surface those visits; **do not** treat missing P50 as 0 planned minutes |

**Executable (#29 / #170):** `SELECT * FROM metric_utilization(240, p_start, p_end)`. Ops: [`ops/sql/metric_utilization.sql`](../../ops/sql/metric_utilization.sql). `over_buffer` = `planned_p90 > buffer_minutes`.

**On the screen (0.6.5, [#228](https://github.com/BOYSABIO/muttmetrics/issues/228)):** bars are **actual** minutes (a fact) against the cap line. A day whose actual minutes pass `buffer_minutes` is drawn as over and counted in the card's header. `over_buffer` (the *planned* worst case) is the planning signal for the day packer; it says nothing while visits carry no estimate, so the screen doesn't use it yet.

### Utilization per week (month view)

| Piece | Definition |
|-------|------------|
| **Grain** | One row per ISO week (Monday, `week_start`) that has visits in the range |
| **Source** | Sums the rows of `metric_utilization` for that week, so a "day" is defined once |
| **Clipping** | `range_start` / `range_end` are the week clipped to the requested range (April's first week reads Apr 1–5, not Mar 30–Apr 5) |
| **Over the cap** | `over_buffer_days` = number of that week's days with `over_buffer`. A weekly total is **never** compared with the daily cap |

**Executable (#178):** `SELECT * FROM metric_utilization_weeks(240, p_start, p_end)`. Returned by the API as `utilization_weeks`; the month view takes each week's grooms and minutes from it as they are. Only the "days over the cap" count comes from the daily rows (actual minutes, see above).

## Named constants

| Name | Value | Used by |
|------|-------|---------|
| `MIN_N` | `5` | Metric functions + `metric_constants.min_n`; API exposes `min_n` on `/metrics/period` (and `/metrics/week`); UI must not hard-code |
| `RECENT_DAYS` | `90` | The recent window for slow questions ([#228](https://github.com/BOYSABIO/muttmetrics/issues/228)): `RECENT_DAYS` in `api/services/metrics.py`; API exposes `recent_days`; UI must not hard-code |

When code lands, this value should appear **once** (e.g. a SQL constant table, a migration-seeded setting, or a single module constant imported by API and tests). Amending the number means amending this table and that single implementation site.

## Scope of M5 (what is in vs out)

**In the product path (#159):** exactly the glossary entries above — €/hour (#27), pivot / overrun / P90 miss (#28), utilization (#29) — plus capture health in [`compliance.md`](./compliance.md). That is the “This week” screen.

**Not in M5 (on purpose):** tip-only totals, client counts, breed mixes, P&L, year views, custom date pickers. Calendar **month** on the same decision metrics is in via [#170](https://github.com/BOYSABIO/muttmetrics/issues/170) (same formulas, longer range). When something new earns a permanent definition (numerator, denominator, eligibility, `MIN_N`), amend **this** runbook first — same rule as #126.

## Techniques / add-ons (#192) — recorded, not sliced yet

Capture can attach catalog techniques to a visit (`visit_add_on` → `add_on`: hand stripping, de-shed, nail grind, …). **Price stays `final_price`** — add-ons are labels for what work happened, not an auto-priced calculator.

| Question | Answer for now |
|----------|----------------|
| Do current €/hour cells include technique? | **No.** `#27` still groups by `condition_score` × `shaved_down` only. A hand-stripped full groom sits in the same coat cell as a normal one. (Since 2026-11-14 the cells are conditions plus one shave-down cell.) |
| Should €/hour be shown **by technique** later? | **Yes, once `n` supports it.** Same eligibility and `MIN_N` as today; a cell would be (at least) one `add_on` within the range — likely `EXISTS` join to `visit_add_on`, not a new fact column. Do not ship a technique slice while most cells sit under `MIN_N`. |
| Does a visit with two add-ons count twice? | Decide when the metric is defined (visit-once vs once-per-technique). Prefer **visit-once** for overall €/hour; technique slices can be “visits that used this add-on.” Amend this runbook before SQL. |

**M7 (#33) dataset builder:** when the feature matrix is exported, include add-on flags (e.g. boolean / categorical columns from `visit_add_on` + `add_on.slug`). Techniques are first-class features for duration/price models — not free text to parse later.

## Learning notes

**Tips vs list price.** Restaurants often separate “sales” (house) from tips (staff). A sole groomer *is* the house — take-home includes tips. For analytics and future models, tip-inflated €/hour can hide weak pricing (“clients tip when they feel guilty about mats”). Defining **both** rates keeps the groomer payoff honest and the analyst lens clean.

**Operational definition.** If SQL, API, and UI disagree on revenue, none of them is “the metric.” This file is the contract.

**Small `n`.** Hiding the average is a feature. Showing a precise €/hour on two visits trains the wrong trust.

**Aggregates don’t compose.** Summing across weeks is fine; averaging weekly averages (or applying `MIN_N` per week then hoping the month is honest) is not. Recompute from visit rows for every range you show (#170).

**Techniques vs coat.** Hand stripping can make €/hour look like a “normal” full groom if you only slice by coat × shaved. Recording the technique (#192) is what makes a later technique slice honest — and what feeds M7 features (#33).

## Related

- Path / exit: [#159](https://github.com/BOYSABIO/muttmetrics/issues/159)
- Range functions: [#155](https://github.com/BOYSABIO/muttmetrics/issues/155) · fixtures: [#16](https://github.com/BOYSABIO/muttmetrics/issues/16)
- Metrics: [#27](https://github.com/BOYSABIO/muttmetrics/issues/27) €/hour · [#28](https://github.com/BOYSABIO/muttmetrics/issues/28) pivot/overrun · [#29](https://github.com/BOYSABIO/muttmetrics/issues/29) utilization
- Techniques / add-ons (record now, slice later): [#192](https://github.com/BOYSABIO/muttmetrics/issues/192) · M7 feature matrix: [#33](https://github.com/BOYSABIO/muttmetrics/issues/33)
- Capture health: [`compliance.md`](./compliance.md) · priors/calibration: [`prior.md`](../prior.md)
- Encoding-safe SQL: [#154](https://github.com/BOYSABIO/muttmetrics/issues/154)
