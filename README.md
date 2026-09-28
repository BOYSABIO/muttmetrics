# MuttMetrics

Duration intelligence for a dog grooming business: structured visit data and P50/P90 duration ranges so the day can be packed against variance — not a booking or CRM system.

**📄 Case study:** [`docs/CASE-STUDY.md`](docs/CASE-STUDY.md) — the problem, the capture-first approach, what a real field trial changed, and where it's heading.

**Stack:** Python · Postgres · SQLAlchemy 2.x · Alembic · FastAPI · Vite + React + TS (capture SPA)  
**Status:** Capture running on real grooms. The React capture SPA ([#69](https://github.com/BOYSABIO/muttmetrics/issues/69)–[#72](https://github.com/BOYSABIO/muttmetrics/issues/72)) is the only groomer UI — Jinja `/capture` retired ([#86](https://github.com/BOYSABIO/muttmetrics/issues/86)). Trial fixes landed: honest SPA/API errors ([#87](https://github.com/BOYSABIO/muttmetrics/issues/87)), timer survives a killed tab ([#88](https://github.com/BOYSABIO/muttmetrics/issues/88)). Photo storage in place ([#30](https://github.com/BOYSABIO/muttmetrics/issues/30), [ADR-002](docs/adr/002-photo-storage.md)). Host remains the maintainer's desktop ([#82](https://github.com/BOYSABIO/muttmetrics/issues/82) runbook). Next: phone photo upload ([#92](https://github.com/BOYSABIO/muttmetrics/issues/92)) and scheduled DB backup ([#95](https://github.com/BOYSABIO/muttmetrics/issues/95)). OptiPlex always-on ([#93](https://github.com/BOYSABIO/muttmetrics/issues/93)) iceboxed until shop ready. CSV backfill deferred.  
**Product framing:** [`docs/VISION.md`](docs/VISION.md) (capture-first, non-goals, later ambition)  
**Data model:** [`docs/schema.md`](docs/schema.md) (tables, relationships, column groups)  
**Local DB peek:** [`docs/ops-db-peek.md`](docs/ops-db-peek.md) (editor + `psql` + starter SELECTs)  
**Enrichment (maintainer):** [`docs/ops-enrichment.md`](docs/ops-enrichment.md) (safe UPDATEs after thin capture)  
**Photo storage (ops):** [`docs/ops-photos.md`](docs/ops-photos.md) (where files live, deletion, orphan sweep — [#30](https://github.com/BOYSABIO/muttmetrics/issues/30))  
**Groomer trial handoff:** [`docs/ops-handoff-trial.md`](docs/ops-handoff-trial.md) (start the stack, phone checklist, troubleshooting — [#82](https://github.com/BOYSABIO/muttmetrics/issues/82))

## Layout

```
docs/CASE-STUDY.md # case study: problem, approach, field trial, direction
docs/VISION.md     # product vision (public)
docs/schema.md     # ER diagram + table reference
docs/ops-db-peek.md # local Postgres peek (editor + starter SQL)
docs/ops-handoff-trial.md # runbook: groomer phone trial over Tailscale
docs/ops-photos.md # photo storage: layout, deletion, sweep
scripts/           # maintenance scripts (SQL recipes, photo purge/sweep)
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
# optional: PHOTO_ROOT (photo files; defaults to ~/muttmetrics-data/photos, outside the repo)

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
