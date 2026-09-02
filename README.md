# MuttMetrics

Duration intelligence for a dog grooming business: structured visit data and P50/P90 duration ranges so the day can be packed against variance — not a booking or CRM system.

**Stack:** Python · Postgres · SQLAlchemy 2.x · Alembic · FastAPI  
**Status:** M1 in progress — schema + query indexes ([#8](https://github.com/BOYSABIO/muttmetrics/issues/8), [#9](https://github.com/BOYSABIO/muttmetrics/issues/9)); seed + CI Postgres ([#11](https://github.com/BOYSABIO/muttmetrics/issues/11)–[#12](https://github.com/BOYSABIO/muttmetrics/issues/12)) next  
**Product framing:** [`docs/VISION.md`](docs/VISION.md) (goals, non-goals, later ambition)  
**Data model:** [`docs/schema.md`](docs/schema.md) (tables, relationships, column groups)

## Layout

```
docs/VISION.md     # product vision (public)
docs/schema.md     # ER diagram + table reference
docs/adr/          # architecture decisions
alembic/           # migration scripts (Alembic)
src/muttmetrics/   # package (models in models/)
tests/
```

## Setup

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -e ".[dev]"
# copy .env.example to .env (Windows: copy .env.example .env)
alembic upgrade head   # apply schema (requires running Postgres)
pytest
ruff check .
ruff format --check .
```

More detail: [`CONTRIBUTING.md`](./CONTRIBUTING.md) (includes Alembic commands). ORM models live in `src/muttmetrics/models/`; see [`docs/schema.md`](docs/schema.md) for the entity diagram.

## Privacy

Owner PII and dog photos are sensitive. Do not commit production dumps or real client CSVs. Use synthetic fixtures in CI.

## License

MIT — [`LICENSE`](./LICENSE)
