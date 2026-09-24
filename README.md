# MuttMetrics

Duration intelligence for a dog grooming business: structured visit data and P50/P90 duration ranges so the day can be packed against variance — not a booking or CRM system.

**Stack:** Python · Postgres · SQLAlchemy 2.x · Alembic · FastAPI  
**Status:** M3.5 handoff — FastAPI + React capture SPA ([#69](https://github.com/BOYSABIO/muttmetrics/issues/69)–[#72](https://github.com/BOYSABIO/muttmetrics/issues/72)); Jinja `/capture` retired ([#86](https://github.com/BOYSABIO/muttmetrics/issues/86)). Next: OptiPlex + Tailscale always-on ([#93](https://github.com/BOYSABIO/muttmetrics/issues/93)), then photo upload and analytics. CSV backfill deferred.  
**Product framing:** [`docs/VISION.md`](docs/VISION.md) (capture-first, non-goals, later ambition)  
**Data model:** [`docs/schema.md`](docs/schema.md) (tables, relationships, column groups)  
**Local DB peek:** [`docs/ops-db-peek.md`](docs/ops-db-peek.md) (editor + `psql` + starter SELECTs)  
**Enrichment (maintainer):** [`docs/ops-enrichment.md`](docs/ops-enrichment.md) (safe UPDATEs after thin capture)  
**Groomer trial handoff:** [`docs/ops-handoff-trial.md`](docs/ops-handoff-trial.md) (start the stack, phone checklist, troubleshooting — [#82](https://github.com/BOYSABIO/muttmetrics/issues/82))

## Layout

```
docs/VISION.md     # product vision (public)
docs/schema.md     # ER diagram + table reference
docs/ops-db-peek.md # local Postgres peek (editor + starter SQL)
docs/ops-handoff-trial.md # runbook: groomer phone trial over Tailscale
docs/adr/          # architecture decisions
docker-compose.yml # local Postgres (primary dev path)
alembic/           # migration scripts (Alembic)
src/muttmetrics/   # package (models/, api/, seed/, …)
frontend/          # Vite + React + TS capture SPA (#69–#72)
scripts/           # shared SQL helpers (cleanup, etc.)
tests/
```

## Setup

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/) for local Postgres.

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -e ".[dev]"
# copy .env.example to .env (Windows: copy .env.example .env)
# .env must include DATABASE_URL and API_KEY

docker compose up -d    # Postgres — container muttmetrics-db (not the old muttmetrics-pg)
alembic upgrade head    # apply schema
python -m muttmetrics.seed  # breed + service reference data (idempotent)
# optional: copy data/pricing.example.json → data/private/pricing.json for local floors

# API — OpenAPI at /docs (maintainer); groomer UI is the React SPA in frontend/
python -m muttmetrics.api
# or: muttmetrics-api
# (reloads src/ only — safe on Windows; bare `uvicorn --reload` can hang)

# React capture UI (second terminal — needs API running on :8000)
cd frontend
copy .env.example .env   # Windows; set VITE_API_KEY = same as root API_KEY
npm install
npm run dev
# open http://127.0.0.1:5173 (dev server — this PC only, fixed port)
# groomer trial instead: npm run build && npm run preview → :5174 (docs/ops-handoff-trial.md)

pytest
ruff check .
ruff format --check .
```

More detail: [`CONTRIBUTING.md`](./CONTRIBUTING.md) (Postgres, Alembic, API, Neon). ORM models: [`docs/schema.md`](docs/schema.md).

## Privacy

Owner PII and dog photos are sensitive. Do not commit production dumps or real client CSVs. Use synthetic fixtures in CI.

## License

MIT — [`LICENSE`](./LICENSE)
