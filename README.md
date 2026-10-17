# MuttMetrics

Duration intelligence for a dog grooming business: structured visit data and P50/P90 duration ranges so the day can be packed against variance — not a booking or CRM system.

**Stack:** Python · Postgres · SQLAlchemy 2.x · Alembic · FastAPI · Vite + React + TS (capture SPA)  
**Status:** Capture is running on real grooms through the React SPA, the only groomer UI. It has photos, backups and a timer that survives a killed tab. M5 ("First Real Numbers") added the groomer's dashboard: week and month views of grooms, time, take-home, €/hour by coat, timing checks and day load. Every number is read from SQL range functions ([ADR-003](docs/architecture/adr/003-metric-views.md), [#158](https://github.com/BOYSABIO/muttmetrics/issues/158), [#170](https://github.com/BOYSABIO/muttmetrics/issues/170)) and hardened in [#177](https://github.com/BOYSABIO/muttmetrics/issues/177)/[#178](https://github.com/BOYSABIO/muttmetrics/issues/178). Next: the M5 measurement window, which asks whether the dashboard changes logging ([#159](https://github.com/BOYSABIO/muttmetrics/issues/159)). The host is still the maintainer's desktop ([#82](https://github.com/BOYSABIO/muttmetrics/issues/82) runbook); the always-on OptiPlex ([#93](https://github.com/BOYSABIO/muttmetrics/issues/93)) is iceboxed until the shop is ready. CSV backfill is deferred.  

## Documentation

📚 **[Docs index](docs/README.md)**

| | |
|---|---|
| **Product** | [Case study](docs/product/case-study.md) · [Vision](docs/product/vision.md) |
| **Architecture** | [Schema](docs/architecture/schema.md) · [Privacy](docs/architecture/privacy.md) · [ADRs](docs/architecture/adr/) · [Rules prior](docs/prior.md) |
| **Runbooks** | [Groomer trial](docs/runbooks/groomer-trial.md) · [DB peek](docs/runbooks/db-peek.md) · [Enrichment](docs/runbooks/enrichment.md) · [Photos](docs/runbooks/photos.md) · [Backups](docs/runbooks/backup.md) · [Compliance](docs/runbooks/compliance.md) · [Analytics](docs/runbooks/analytics.md) · [Migrations](docs/runbooks/migrations.md) |
| **Ops** | [Ops map](ops/README.md) — backup, photos, SQL recipes; package CLIs stay in `src/` |
| **Contributing** | [Setup](#setup) · [CONTRIBUTING](./CONTRIBUTING.md) |
| **Planning** | [Milestones](https://github.com/BOYSABIO/muttmetrics/milestones) · [Issues](https://github.com/BOYSABIO/muttmetrics/issues) |

## Layout

```
docs/               # documentation — start at docs/README.md
  product/          #   vision, case study
  architecture/     #   schema, privacy, adr/
  runbooks/         #   step-by-step operating procedures
src/muttmetrics/    # package (api/, models/, priors/, media/, seed/, …)
alembic/            # migration scripts (Alembic)
frontend/           # Vite + React + TS capture SPA (#69–#72)
ops/                # maintainer tooling — start at ops/README.md (#125)
tests/              # api/ (HTTP+DB), unit/, fixtures/ (synthetic metric week)
docker-compose.yml  # local Postgres (primary dev path)
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
# groomer trial instead: npm run build && npm run preview → :5174 (docs/runbooks/groomer-trial.md)

pytest                   # runs against muttmetrics_test, never the dev DB (setup: CONTRIBUTING)
ruff check .
ruff format --check .
```

More detail: [`CONTRIBUTING.md`](./CONTRIBUTING.md) (Postgres, Alembic, API, Neon). ORM models: [`docs/architecture/schema.md`](docs/architecture/schema.md).

## Privacy

Owner PII and dog photos are sensitive. Do not commit production dumps or real client CSVs. Use synthetic fixtures in CI.

## License

MIT — [`LICENSE`](./LICENSE)
