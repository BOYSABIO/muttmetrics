# MuttMetrics — vision

Public product framing for this repo. Deep design notes stay local; **what to build next** lives in [milestones](https://github.com/BOYSABIO/muttmetrics/milestones) and [issues](https://github.com/BOYSABIO/muttmetrics/issues).

## Thesis

A single-groomer salon caps its day because job duration is unpredictable. MuttMetrics converts that **variance tax** back into capacity by predicting a **duration range (P50 / P90)** per booking and packing the day against the sum of those ranges — not a single guess.

Own the structured dog/visit data. Everything valuable in this project is a read on that data.

## Adoption path

Start from an **empty database**. Grow row-by-row as grooms happen — that is the only low-friction way for a working groomer to adopt.

- **Not the plan:** evening Excel/CSV backfills of historical grooms as the primary path
- **The plan:** after each groom, a **lightweight on-job form** (phone browser) writes a visit row
- **CSV import** stays an optional escape hatch later if bulk load is ever needed — not how we start

Compliance (visit rows actually exist) is the product gate. Fancy UI and booking come after that loop is real.

## Near-term goals (build order)

1. **Canonical schema** — owner / dog / visit (+ breed, service priors) — done for M1
2. **Capture** — FastAPI `POST /visits` + React phone SPA; every completed groom becomes a row
3. **Rules-based P50/P90** — honest breed-based cold start before any ML; log prediction error from day one
4. **Analytics** — overrun, pivots, €/hour by condition — findings the groomer can act on
5. **Day packing** — “can I take a third dog?” against summed P90

**Amendment (2026-10-06):** The rules prior may key off breed for cold start. Later fitted predictions (M7) should not *require* breed — **coat, size, and temperament/handling** (plus visit context) are the intended primary drivers, especially for mixes. See [#121](https://github.com/BOYSABIO/muttmetrics/issues/121).

**Amendment (2026-10-07):** Between M4 and M5 sits **[M4.5 — Data clarity & ops hygiene](https://github.com/BOYSABIO/muttmetrics/milestone/13)**: lock groomer-facing scales (e.g. `condition_score` 0 = worst … 5 = best, [#123](https://github.com/BOYSABIO/muttmetrics/issues/123)), scripts discoverability, and a later ops-tree overhaul. **Do not** turn the visit form into a dog/owner CRM; enrich via maintainer tools when needed ([#127](https://github.com/BOYSABIO/muttmetrics/issues/127), [#117](https://github.com/BOYSABIO/muttmetrics/issues/117)). Empty nullable columns are fine; ambiguous labels are not. Recompute/derived jobs wait until there is data worth recomputing.

**Amendment (2026-10-07, evening):** After thin capture works, the bottleneck is **incomplete entity rows** (dog/owner), not missing charts. **[M4.75 — Dog/owner directory](https://github.com/BOYSABIO/muttmetrics/milestone/14)** ([#117](https://github.com/BOYSABIO/muttmetrics/issues/117)): same product shell, **separate areas** — Visits (unchanged capture) vs Directory (profiles + safe edits). That is hand backfill for a shop with **no Excel history** (M2 CSV stays deferred). M5 renamed to **fact-table metric stubs (SQL)** — definitions/scripts, not a BI milestone; in-app analytics later ([#130](https://github.com/BOYSABIO/muttmetrics/issues/130)). Do not rush M6/M7 “for when data is ready” while enrichment is still SQL-only and only the maintainer can practically thicken rows.

**Amendment (2026-10-10):** M4.75 Directory **shipped** (API [#131](https://github.com/BOYSABIO/muttmetrics/issues/131)/[#132](https://github.com/BOYSABIO/muttmetrics/issues/132), SPA [#138](https://github.com/BOYSABIO/muttmetrics/issues/138)–[#140](https://github.com/BOYSABIO/muttmetrics/issues/140)). Enrichment default is Directory; SQL remains an escape hatch ([`enrichment.md`](../runbooks/enrichment.md), [#141](https://github.com/BOYSABIO/muttmetrics/issues/141)). The evening note above is historical context for *why* M4.75 was pulled ahead of M5.

Stack for that path: Python, Postgres, SQLAlchemy, Alembic, FastAPI. Groomer capture UI path (teach + build): **A** thin HTML/Jinja ([#63](https://github.com/BOYSABIO/muttmetrics/issues/63)) → **B** Vite + React + TS SPA ([#69](https://github.com/BOYSABIO/muttmetrics/issues/69)) → **C** Next graduate for owner surfaces ([#41](https://github.com/BOYSABIO/muttmetrics/issues/41)). Same Python API throughout.

**Amendment (2026-09-24):** Stage **A** is retired — Jinja `/capture` removed in [#86](https://github.com/BOYSABIO/muttmetrics/issues/86). **B** (React SPA) is the only groomer capture UI. **C** remains later for owner surfaces.

**OpenAPI `/docs`** is the maintainer’s API test console — not the groomer’s salon UI.

## Non-goals (for now)

These are **not** what MuttMetrics is *today*, and they are not the next milestones:

- Booking calendar / appointment management as the current product
- Invoicing, payments, deposits
- WhatsApp/SMS CRM or blast messaging
- Becoming a full salon OS before capture + prediction work

“Non-goal for now” ≠ “never.” See **Later ambition** below.

If scheduling is built later, it is built **in-house**, with MuttMetrics still owning duration intelligence, rather than bolted onto a third-party salon suite.

## Later ambition

Longer-range ideas are kept deliberately general here. The concrete ones sit in the **M10 — Icebox** milestone, so they stay out of the way of the capture-first path.

- **Scheduling that uses the ranges:** duration predictions feeding how the day is actually booked.
- **Richer inputs:** intake photos and condition, and fitted models once there's enough data to beat the rules — scoring from coat/size/temperament without requiring breed ([#121](https://github.com/BOYSABIO/muttmetrics/issues/121)).
- **An owner-facing layer:** built on the same data, only after capture and prediction work.
- **Beyond one shop:** only if the single-shop loop is proven.

The end state is an **intelligence layer on owned data**, not a salon suite.

## How to read the repo

| Artifact | Use |
|----------|-----|
| This file | Why the project exists; boundaries; long-range ambition |
| GitHub milestones / issues | What to do next |
| `docs/architecture/adr/` | Engineering decisions (stack, schema policies, …) |
| README | Setup and one-line pitch |

## Success signals

- Visit rows actually get entered after grooms (phone form, not spreadsheet homework)
- Dog/owner profiles can be thickened in **Directory** without SQL (hand backfill when there was never Excel)
- Predicted ranges exist and calibration is measurable
- Schedule decisions use P90, not a hard “max 2 forever”
- Scope stays on data + prediction first; booking/invoicing/UI polish after capture + enrichment are real
