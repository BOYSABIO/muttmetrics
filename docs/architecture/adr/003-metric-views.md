# Architecture Decision Record

## ADR-003: Metric definitions live in Postgres views

- **Status:** Accepted
- **Date:** 2026-10-14
- **Context:** M5 metrics ([#159](https://github.com/BOYSABIO/muttmetrics/issues/159)) are read in four places: ops SQL recipes, the API (`GET /metrics/week`), the “This week” dashboard, and tests. If each reader carries its own formula, they will drift — the screen and [`analytics.md`](../../runbooks/analytics.md) will disagree and nobody will know which is right. [#130](https://github.com/BOYSABIO/muttmetrics/issues/130) already asked for a single source of truth. Definitions and `MIN_N` are locked in the glossary ([#126](https://github.com/BOYSABIO/muttmetrics/issues/126)); fixtures with hand-computed answers exist ([#16](https://github.com/BOYSABIO/muttmetrics/issues/16)). This ADR chooses **where the executable definition lives** before the first metric view ships ([#155](https://github.com/BOYSABIO/muttmetrics/issues/155)).

### Decision

**Metric formulas live in Postgres — SQL views created by Alembic migrations — so every reader runs the same definition.**

1. **Views for parameter-free metrics.** Readers use `SELECT … FROM metric_…`. Examples: week summary, €/hour by condition × shaved, pivot / overrun / P90 miss. The glossary remains the prose contract; the view is the executable one.
2. **SQL functions when a parameter is required.** Views cannot take arguments. Utilization needs `buffer_minutes` ([#29](https://github.com/BOYSABIO/muttmetrics/issues/29)) → e.g. `metric_utilization(buffer_minutes int)`, not a view. Same migration discipline; same “one definition” rule.
3. **`MIN_N` is enforced inside those SQL objects** for averages and rates (`CASE WHEN n < 5 THEN NULL` or equivalent). Totals and counts always show. The API/UI may label a NULL rate as “not enough grooms yet”; they must **not** re-implement the threshold. One place decides honesty — otherwise `psql` can still show a lying average while the dashboard hides it.
4. **`MIN_N = 5` stays the named product constant** from the glossary. Until a shared settings table exists, the literal appears only inside metric views/functions (and the fixture `EXPECTED`), not scattered through Python route handlers.
5. **Changing a definition is a migration.** Same columns → `CREATE OR REPLACE VIEW`. Different columns → `DROP VIEW` then `CREATE VIEW`. `downgrade()` drops the object.

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

- Metric issues (#27–#29) **cite the glossary** for meaning and **select from these objects** for numbers. They do not embed a second formula in Python except to call the view/function.
- The first view that proves the plumbing is **`metric_week_summary`**: eligible visits, groomed minutes, and revenue per ISO week (status rule from the glossary). Later views follow the same migration + fixture-test pattern.
- **`DROP VIEW` in `upgrade()` will trip the migration-safety guard** ([#89](https://github.com/BOYSABIO/muttmetrics/issues/89), `tests/unit/test_migration_safety.py`). That is expected: dropping a view loses **no table data**. The correct response is an acknowledgement line in the migration, e.g. `# migration-safety: reviewed - replace metric view columns, see #155` — **not** weakening the guard.
- Alembic round-trip (`downgrade -1` then `upgrade head`) must recreate the views cleanly.
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
