# MuttMetrics

Duration intelligence for a dog grooming business: structured visit data and P50/P90 duration ranges so the day can be packed against variance — not a booking or CRM system.

**Stack:** Python · Postgres · SQLAlchemy 2.x · Alembic · FastAPI  
**Status:** M3 capture — FastAPI, auth, `POST /visits`, create-or-get owners/dogs ([#18](https://github.com/BOYSABIO/muttmetrics/issues/18)–[#21](https://github.com/BOYSABIO/muttmetrics/issues/21)). Next: phone form ([#63](https://github.com/BOYSABIO/muttmetrics/issues/63)). CSV backfill deferred.  
**Product framing:** [`docs/VISION.md`](docs/VISION.md) (capture-first, non-goals, later ambition)  
**Data model:** [`docs/schema.md`](docs/schema.md) (tables, relationships, column groups)

## Layout

```
docs/VISION.md     # product vision (public)
docs/schema.md     # ER diagram + table reference
docs/adr/          # architecture decisions
docker-compose.yml # local Postgres (primary dev path)
alembic/           # migration scripts (Alembic)
src/muttmetrics/   # package (models/, api/, seed/, …)
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

# API — OpenAPI UI at http://127.0.0.1:8000/docs  (developer console, not salon UI)
python -m muttmetrics.api
# or: muttmetrics-api
# (reloads src/ only — safe on Windows; bare `uvicorn --reload` can hang)

pytest
ruff check .
ruff format --check .
```

More detail: [`CONTRIBUTING.md`](./CONTRIBUTING.md) (Postgres, Alembic, API, Neon). ORM models: [`docs/schema.md`](docs/schema.md).

## Privacy

Owner PII and dog photos are sensitive. Do not commit production dumps or real client CSVs. Use synthetic fixtures in CI.

## License

MIT — [`LICENSE`](./LICENSE)
