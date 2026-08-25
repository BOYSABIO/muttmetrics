# MuttMetrics

> A data layer for a real grooming business. Not a booking system — an intelligence layer that answers: **what am I actually walking into, and how long will it really take?**

**Status:** Scaffold. Schema and capture come next — see GitHub milestones.  
**Design doc:** `docs/about.md` lives locally only (gitignored) — thesis, full data model, build sequence. Public source of truth for *what to build* is the GitHub milestones/issues.  
**Stack:** Python · Postgres · SQLAlchemy 2.x · Alembic · FastAPI (thin API when needed).

## Thesis (one line)

Predict a **duration range (P50 / P90)** per booking so the day can be packed against variance — converting insurance capacity back into a third groom when the risk is low.

## Non-goals

MuttMetrics does **not** manage bookings, invoices, payments, or customer messaging. It owns structured dog/visit data and tells you how long to block. If that ever needs a booking product, buy one and integrate — do not become a worse MoeGo.

## Repo layout

```
docs/about.md            # local-only design doc (gitignored)
docs/adr/                # architecture decision records (why we chose X)
src/muttmetrics/         # Python package (grows with milestones)
tests/                   # pytest
```

## Local setup (scaffold)

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -e ".[dev]"
pytest
ruff check .
```

Database, migrations, and seed land in **M1** (see milestones). Do not invent a parallel schema outside Alembic.

## Privacy

Real German business data: owner PII and dog photos are GDPR-sensitive. Never commit production dumps or real client CSVs. Use `data/private/` locally (gitignored) and synthetic fixtures in CI.

## License

MIT — see [`LICENSE`](./LICENSE).
