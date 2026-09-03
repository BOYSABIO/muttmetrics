# MuttMetrics

Duration intelligence for a dog grooming business: structured visit data and P50/P90 duration ranges so the day can be packed against variance — not a booking or CRM system.

**Stack:** Python · Postgres · SQLAlchemy 2.x · Alembic · FastAPI  
**Status:** M1 in progress — schema + seed ([#8](https://github.com/BOYSABIO/muttmetrics/issues/8)–[#11](https://github.com/BOYSABIO/muttmetrics/issues/11)); CI migrate ([#12](https://github.com/BOYSABIO/muttmetrics/issues/12)) next  
**Product framing:** [`docs/VISION.md`](docs/VISION.md) (goals, non-goals, later ambition)  
**Data model:** [`docs/schema.md`](docs/schema.md) (tables, relationships, column groups)

## Layout

```
docs/VISION.md     # product vision (public)
docs/schema.md     # ER diagram + table reference
docs/adr/          # architecture decisions
docker-compose.yml # local Postgres (primary dev path)
alembic/           # migration scripts (Alembic)
src/muttmetrics/   # package (models in models/)
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

docker compose up -d    # Postgres — wait until healthy (docker compose ps)
alembic upgrade head    # apply schema
python -m muttmetrics.seed  # breed + service reference data (idempotent)
pytest
ruff check .
ruff format --check .
```

More detail: [`CONTRIBUTING.md`](./CONTRIBUTING.md) (Postgres, Alembic, Neon alternative). ORM models: [`docs/schema.md`](docs/schema.md).

## Privacy

Owner PII and dog photos are sensitive. Do not commit production dumps or real client CSVs. Use synthetic fixtures in CI.

## License

MIT — [`LICENSE`](./LICENSE)
