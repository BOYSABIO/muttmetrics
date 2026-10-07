# MuttMetrics

Duration intelligence for a dog grooming business: structured visit data and P50/P90 duration ranges so the day can be packed against variance — not a booking or CRM system.

**Stack:** Python · Postgres · SQLAlchemy 2.x · Alembic · FastAPI · Vite + React + TS (capture SPA)  
**Status:** Capture running on real grooms. The React capture SPA ([#69](https://github.com/BOYSABIO/muttmetrics/issues/69)–[#72](https://github.com/BOYSABIO/muttmetrics/issues/72)) is the only groomer UI — Jinja `/capture` retired ([#86](https://github.com/BOYSABIO/muttmetrics/issues/86)). Trial fixes landed: honest SPA/API errors ([#87](https://github.com/BOYSABIO/muttmetrics/issues/87)), timer survives a killed tab ([#88](https://github.com/BOYSABIO/muttmetrics/issues/88)). Photo capture end to end: storage ([#30](https://github.com/BOYSABIO/muttmetrics/issues/30), [ADR-002](docs/architecture/adr/002-photo-storage.md)) and phone upload from camera or library ([#92](https://github.com/BOYSABIO/muttmetrics/issues/92)). Host remains the maintainer's desktop ([#82](https://github.com/BOYSABIO/muttmetrics/issues/82) runbook). Backups in place ([#95](https://github.com/BOYSABIO/muttmetrics/issues/95)): dump + photo copy, retention, staleness check — run manually for now, scheduling documented. Next: M3.5 exit checks ([#84](https://github.com/BOYSABIO/muttmetrics/issues/84)). OptiPlex always-on ([#93](https://github.com/BOYSABIO/muttmetrics/issues/93)) iceboxed until shop ready. CSV backfill deferred.  

## Documentation

📚 **[Docs index](docs/README.md)**

| | |
|---|---|
| **Product** | [Case study](docs/product/case-study.md) · [Vision](docs/product/vision.md) |
| **Architecture** | [Schema](docs/architecture/schema.md) · [Privacy](docs/architecture/privacy.md) · [ADRs](docs/architecture/adr/) · [Rules prior](docs/prior.md) |
| **Runbooks** | [Groomer trial](docs/runbooks/groomer-trial.md) · [DB peek](docs/runbooks/db-peek.md) · [Enrichment](docs/runbooks/enrichment.md) · [Photos](docs/runbooks/photos.md) · [Backups](docs/runbooks/backup.md) · [Compliance](docs/runbooks/compliance.md) |
| **Scripts** | [Scripts map](scripts/README.md) — backup, photos, SQL recipes, package CLIs |
| **Contributing** | [Setup](#setup) · [CONTRIBUTING](./CONTRIBUTING.md) |
| **Planning** | [Milestones](https://github.com/BOYSABIO/muttmetrics/milestones) · [Issues](https://github.com/BOYSABIO/muttmetrics/issues) |

## Layout

```
docs/               # documentation — start at docs/README.md
  product/          #   vision, case study
  architecture/     #   schema, privacy, adr/
  runbooks/         #   step-by-step operating procedures
src/muttmetrics/    # package (models/, api/, seed/, …)
alembic/            # migration scripts (Alembic)
frontend/           # Vite + React + TS capture SPA (#69–#72)
scripts/            # ops — start at scripts/README.md (Python + SQL + CLI map)
tests/
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

pytest
ruff check .
ruff format --check .
```

More detail: [`CONTRIBUTING.md`](./CONTRIBUTING.md) (Postgres, Alembic, API, Neon). ORM models: [`docs/architecture/schema.md`](docs/architecture/schema.md).

## Privacy

Owner PII and dog photos are sensitive. Do not commit production dumps or real client CSVs. Use synthetic fixtures in CI.

## License

MIT — [`LICENSE`](./LICENSE)
