# Architecture Decision Record

## ADR-003: Metric definitions live in Postgres (views → range functions)

- **Status:** Accepted (amended 2026-10-16 for [#170](https://github.com/BOYSABIO/muttmetrics/issues/170))
- **Date:** 2026-10-14
- **Context:** M5 metrics ([#159](https://github.com/BOYSABIO/muttmetrics/issues/159)) are read in four places: ops SQL recipes, the API (`GET /metrics/week` / `GET /metrics/period`), the dashboard, and tests. If each reader carries its own formula, they will drift — the screen and [`analytics.md`](../../runbooks/analytics.md) will disagree and nobody will know which is right. [#130](https://github.com/BOYSABIO/muttmetrics/issues/130) already asked for a single source of truth. Definitions and `MIN_N` are locked in the glossary ([#126](https://github.com/BOYSABIO/muttmetrics/issues/126)); fixtures with hand-computed answers exist ([#16](https://github.com/BOYSABIO/muttmetrics/issues/16)). This ADR chooses **where the executable definition lives** before the first metric object ships ([#155](https://github.com/BOYSABIO/muttmetrics/issues/155)).

### Decision

**Metric formulas live in Postgres — SQL objects created by Alembic migrations — so every reader runs the same definition.**

1. **Range functions are the executable definition (#170).** Each metric is `metric_*(p_start date, p_end date)` (inclusive). A week is `(monday, monday+6)`; a calendar month is `(1st, last day)`; any other range is the same call with different args. There is **no** `metric_week_*` / `metric_month_*` twin pair — averages and `MIN_N` do not compose across groupings, so the definition must take a range.
2. **Utilization takes buffer + range:** `metric_utilization(buffer_minutes, p_start, p_end)` so a month only returns that month’s days.
3. **`MIN_N` is enforced inside those SQL objects** for averages and rates (`CASE WHEN n < (SELECT min_n FROM metric_constants) THEN NULL`). Totals and counts always show. The API/UI may label a NULL rate as “not enough grooms yet”; they must **not** re-implement the threshold.
4. **`MIN_N = 5` stays the named product constant** from the glossary, stored in `metric_constants` and mirrored in fixture `EXPECTED` — not scattered through Python route handlers.
5. **Changing a definition is a migration.** `CREATE OR REPLACE FUNCTION` when the signature is stable; otherwise `DROP` then `CREATE`. `downgrade()` restores the previous objects.

### Amendment (#170) — why functions replaced week views

The first shipping form (#155–#158) used week-grouped **views** (`date_trunc('week', …)`). That locked the dashboard to ISO weeks. At early capture volume most weekly averages sit under `MIN_N`; a **month** crosses the threshold sooner. You cannot build a honest month by averaging weekly rows (weeks cross month boundaries; `MIN_N` must be judged on the month’s own `n`). Option A (copy each view as `metric_month_*`) doubles every formula. **Option B (range functions) won:** one definition per metric; week behaviour is unchanged as `(Mon, Mon+6)`.

### Why views (A) over a Python query module (B)

| | **A — SQL views (chosen)** | **B — Python / SQLAlchemy module** |
|--|----------------------------|-------------------------------------|
| **Who can run it** | Anyone with `psql` / the Postgres extension — no app process | Needs the Python package / CLI |
| **Ops recipes** | Stay plain `SELECT` from the view ([#154](https://github.com/BOYSABIO/muttmetrics/issues/154) encoding-safe path) | Recipes would call a CLI or duplicate SQL |
| **Drift risk** | Low if everyone selects from the view | Low *inside* the app; high if ops SQL is rewritten “just once” |
| **Versioning** | Travels with schema (Alembic); prod and local upgrade together | Code deploy; DB can lag or disagree with old recipes |
| **Testing** | Load fixtures → `SELECT` → compare to hand-computed `EXPECTED` | Easy unit tests on Python; still need a DB integration test for truth |
| **Fit with ADR-001** | Visit stays the fact table; analytics are **read models** on top (views), not stored derived columns on `owner`/`dog` | Also fine conceptually; weaker for maintainer SQL |

**Option C (materialized views / summary tables)** is rejected for v1: salon volume is tiny; refresh logic is cost without benefit.

We chose **A** so the groomer’s weekly numbers, the maintainer peeking in Postgres, and CI all share one definition — and so ops never becomes a second formula language.

### Consequences

- Metric issues (#27–#29) **cite the glossary** for meaning and **select from these objects** for numbers. They do not embed a second formula in Python except to call the function.
- API: `GET /metrics/period?start=&end=` is the general reader; `GET /metrics/week` is a thin wrapper that sets the Mon–Sun range and still returns `previous_week`.
- Ops recipes call `FROM metric_summary(…)` (etc.) with an explicit range — see [`analytics.md`](../../runbooks/analytics.md).
- **`DROP VIEW` / `DROP FUNCTION` in `upgrade()` will trip the migration-safety guard** ([#89](https://github.com/BOYSABIO/muttmetrics/issues/89)). That is expected when replacing read models (no table data lost). Acknowledge in the migration header — **not** weaken the guard.
- Alembic round-trip (`downgrade -1` then `upgrade head`) must recreate the objects cleanly.
- Privacy unchanged: definitions are public; real salon volumes stay in `docs/notes/` ([`analytics.md`](../../runbooks/analytics.md)).

### Alternatives considered

- **B — Python query module as source of truth** — rejected above; revisit only if ops SQL is abandoned entirely.
- **C — Materialized views / nightly summary tables** — rejected at this volume; adds refresh and staleness without payoff.
- **`MIN_N` only in the API** — rejected: `psql` and ops recipes could still display averages over `n < 5` as if they were KPIs.
- **`MIN_N` in both SQL and Python** — rejected: two thresholds will diverge.

### Follow-ups

- Migration + test for `metric_week_summary` ([#155](https://github.com/BOYSABIO/muttmetrics/issues/155)).
- Metric views/functions for [#27](https://github.com/BOYSABIO/muttmetrics/issues/27)–[#29](https://github.com/BOYSABIO/muttmetrics/issues/29).
- API [#156](https://github.com/BOYSABIO/muttmetrics/issues/156) reads views; dashboard [#158](https://github.com/BOYSABIO/muttmetrics/issues/158) displays NULL rates honestly.
