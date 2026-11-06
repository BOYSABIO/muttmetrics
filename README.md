# MuttMetrics

Duration intelligence for a dog grooming business: structured visit data and P50/P90 duration ranges so the day can be packed against variance — not a booking or CRM system.

**Stack:** Python · Postgres · SQLAlchemy 2.x · Alembic · FastAPI · Vite + React + TS (capture SPA)  
**Status:** Capture runs on real grooms through the React SPA, the only groomer UI, with photos, backups and a timer that survives a killed tab. M5 added the groomer's dashboard (week and month views read from SQL range functions, [ADR-003](docs/architecture/adr/003-metric-views.md)). M6 ("production-ready") made it run for real: versioned releases, a one-command deploy and rollback, GDPR export/erase, cats and other species, add-ons, editing a visit. Since 2026-11 it runs on an **always-on home server** reached only over Tailscale ([#93](https://github.com/BOYSABIO/muttmetrics/issues/93), [home-server runbook](docs/runbooks/home-server.md)). Next: monitoring ([#104](https://github.com/BOYSABIO/muttmetrics/issues/104)) and the encrypted off-site backup ([#221](https://github.com/BOYSABIO/muttmetrics/issues/221)).

## Documentation

📚 **[Docs index](docs/README.md)**

| | |
|---|---|
| **Product** | [Case study](docs/product/case-study.md) · [Vision](docs/product/vision.md) |
| **Architecture** | [Schema](docs/architecture/schema.md) · [Privacy](docs/architecture/privacy.md) · [ADRs](docs/architecture/adr/) · [Rules prior](docs/prior.md) |
| **Runbooks** | [Home server](docs/runbooks/home-server.md) · [Groomer access](docs/runbooks/groomer-access.md) · [Release](docs/runbooks/release.md) · [DB peek](docs/runbooks/db-peek.md) · [Enrichment](docs/runbooks/enrichment.md) · [Photos](docs/runbooks/photos.md) · [Backups](docs/runbooks/backup.md) · [Compliance](docs/runbooks/compliance.md) · [Analytics](docs/runbooks/analytics.md) · [Migrations](docs/runbooks/migrations.md) |
| **Ops** | [Ops map](ops/README.md) — backup, photos, SQL recipes; package CLIs stay in `src/` · [Server config](ops/server/README.md) |
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
copy .env.example .env   # Windows; optional VITE_BUSINESS_NAME only — API_KEY stays in repo-root .env (#194)
npm install
npm run dev
# open http://127.0.0.1:5173 (dev server — this PC only, fixed port)
# production runs on the home server, deployed from a tag (docs/runbooks/release.md)

pytest                   # runs against muttmetrics_test, never the dev DB (setup: CONTRIBUTING)
ruff check .
ruff format --check .
```

More detail: [`CONTRIBUTING.md`](./CONTRIBUTING.md) (Postgres, Alembic, API, Neon). ORM models: [`docs/architecture/schema.md`](docs/architecture/schema.md).

## Privacy

Owner PII and dog photos are sensitive. Do not commit production dumps or real client CSVs. Use synthetic fixtures in CI.

## License

MIT — [`LICENSE`](./LICENSE)
