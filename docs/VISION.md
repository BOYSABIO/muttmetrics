# MuttMetrics — vision

Public product framing for this repo. Deep design notes stay local; **what to build next** lives in [milestones](https://github.com/BOYSABIO/muttmetrics/milestones) and [issues](https://github.com/BOYSABIO/muttmetrics/issues).

## Thesis

Sebastian caps at two grooms per day because he cannot predict which jobs will blow up. MuttMetrics converts that **variance tax** back into capacity by predicting a **duration range (P50 / P90)** per booking and packing the day against the sum of those ranges — not a single guess.

Own the structured dog/visit data. Everything valuable in this project is a read on that data.

## Adoption path

Start from an **empty database**. Grow row-by-row as grooms happen — that is the only low-friction way for Sebastian to adopt.

- **Not the plan:** evening Excel/CSV backfills of historical grooms as the primary path
- **The plan:** after each groom, a **lightweight on-job form** (phone browser) writes a visit row
- **CSV import** stays an optional escape hatch later if bulk load is ever needed — not how we start

Compliance (visit rows actually exist) is the product gate. Fancy UI and booking come after that loop is real.

## Near-term goals (build order)

1. **Canonical schema** — owner / dog / visit (+ breed, service priors) — done for M1
2. **Capture** — FastAPI `POST /visits`, then a minimal phone form; every completed groom becomes a row
3. **Rules-based P50/P90** — honest priors before any ML; log prediction error from day one
4. **Analytics** — overrun, pivots, €/hour by condition — findings Sebastian can act on
5. **Day packing** — “can I take a third dog?” against summed P90

Stack for that path: Python, Postgres, SQLAlchemy, Alembic, FastAPI. Groomer capture UI starts as a thin HTML form; owner-facing surfaces may graduate to TypeScript later.

**OpenAPI `/docs`** is Spencer’s API test console — not Sebastian’s salon UI.

## Non-goals (for now)

These are **not** what MuttMetrics is *today*, and they are not the next milestones:

- Booking calendar / appointment management as the current product
- Invoicing, payments, deposits
- WhatsApp/SMS CRM or blast messaging
- Becoming a full salon OS before capture + prediction work

“Non-goal for now” ≠ “never.” See **Later ambition** below.

We do **not** plan to buy MoeGo/Petleo and bolt on. If scheduling/booking is built later, it is **in-house** (salon website / calendar), with MuttMetrics still owning duration intelligence.

## Later ambition

Ideas we intend to keep alive. Many are already filed under milestone **M10 — Icebox** so they stay concrete on GitHub without blocking the capture-first path.

| Theme | Direction |
|--------|-----------|
| Phone capture UI | Better mobile form after the ugly v0 that proves compliance |
| In-house booking / calendar | Website-facing booking integrated with how the salon already works — not a third-party suite |
| WhatsApp | Optional intake/booking channel; **website remains primary** when booking exists |
| CSV / bulk import | Optional tooling if historical dump is ever needed |
| Photo at booking | Intake photos, manual condition score, matting report — pivot before the door |
| Fitted model | Replace rules when `n` justifies it; beat the baseline or keep the prior |
| Owner layer | Care protocols, dog-specific intervals, salon-branded dog pages |
| Vision | Models on intake photos once labels exist |
| Duration → schedule | Push P50/P90 into the in-house calendar so blocks match reality |
| Retail | Product recommendations as the end of care advice — not banners |
| Multi-salon | Only if the single-shop loop is proven |
| Content | Before/after cards, equipment ROI from utilization data |
| Consumables / inventory | Shampoo, conditioner, creams, tools — COGS and equipment ROI adjacency (icebox) |
| Salon cost base / P&L context | Rent, utilities, and similar fixed costs as analytics context for pricing and capacity — **not** invoicing or payments |

The ambitious end-state is still an **intelligence layer on owned data**, with booking built ourselves when we need it — not a rush to clone a salon suite.

## How to read the repo

| Artifact | Use |
|----------|-----|
| This file | Why the project exists; boundaries; long-range ambition |
| GitHub milestones / issues | What to do next |
| `docs/adr/` | Engineering decisions (stack, schema policies, …) |
| README | Setup and one-line pitch |

## Success signals

- Visit rows actually get entered after grooms (phone form, not spreadsheet homework)
- Predicted ranges exist and calibration is measurable
- Schedule decisions use P90, not a hard “max 2 forever”
- Scope stays on data + prediction first; booking/UI polish after compliance is real
