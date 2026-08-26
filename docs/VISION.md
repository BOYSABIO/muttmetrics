# MuttMetrics — vision

Public product framing for this repo. Deep design notes stay local; **what to build next** lives in [milestones](https://github.com/BOYSABIO/muttmetrics/milestones) and [issues](https://github.com/BOYSABIO/muttmetrics/issues).

## Thesis

Sebastian caps at two grooms per day because he cannot predict which jobs will blow up. MuttMetrics converts that **variance tax** back into capacity by predicting a **duration range (P50 / P90)** per booking and packing the day against the sum of those ranges — not a single guess.

Own the structured dog/visit data. Everything valuable in this project is a read on that data.

## Near-term goals (build order)

1. **Canonical schema** — owner / dog / visit (+ breed, service priors)
2. **Capture** — every completed groom becomes a row (compliance is the product)
3. **Rules-based P50/P90** — honest priors before any ML; log prediction error from day one
4. **Analytics** — overrun, pivots, €/hour by condition — findings Sebastian can act on
5. **Day packing** — “can I take a third dog?” against summed P90

Stack for that path: Python, Postgres, SQLAlchemy, Alembic, FastAPI. Owner-facing UI graduates to TypeScript later.

## Non-goals (for now)

These are **not** what MuttMetrics is, and they are not the next milestones:

- Booking calendar / appointment management as a product
- Invoicing, payments, deposits
- WhatsApp/SMS CRM or blast messaging
- Replacing MoeGo, Petleo, or similar salon suites

If scheduling software is needed later, **buy it and integrate** — tell it how long to block; do not become a worse booking app.

“Non-goal for now” ≠ “never.” See **Later ambition** below.

## Later ambition

Ideas we intend to keep alive. Many are already filed under milestone **M10 — Icebox** so they stay concrete on GitHub without blocking M1–M9.

| Theme | Direction |
|--------|-----------|
| Photo at booking | Intake photos, manual condition score, matting report — pivot before the door |
| Fitted model | Replace rules when `n` justifies it; beat the baseline or keep the prior |
| Owner layer | Care protocols, dog-specific intervals, salon-branded dog pages |
| Vision | Models on intake photos once labels exist |
| Integrations | Push duration guidance into real booking tools |
| Retail | Product recommendations as the end of care advice — not banners |
| Multi-salon | Only if the single-shop loop is proven |
| Content | Before/after cards, equipment ROI from utilization data |

The ambitious end-state is still an **intelligence layer** on owned data — not a full salon OS.

## How to read the repo

| Artifact | Use |
|----------|-----|
| This file | Why the project exists; boundaries; long-range ambition |
| GitHub milestones / issues | What to do next |
| `docs/adr/` | Engineering decisions (stack, schema policies, …) |
| README | Setup and one-line pitch |

## Success signals

- Visit rows actually get entered after grooms
- Predicted ranges exist and calibration is measurable
- Schedule decisions use P90, not a hard “max 2 forever”
- Scope stays on data + prediction; booking/CRM stays out of the critical path
