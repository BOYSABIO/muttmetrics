# MuttMetrics

Duration intelligence for a dog grooming business: structured visit data and P50/P90 duration ranges so the day can be packed against variance — not a booking or CRM system.

**Stack:** Python · Postgres · SQLAlchemy 2.x · Alembic · FastAPI  
**Status:** Scaffold — see [milestones](https://github.com/BOYSABIO/muttmetrics/milestones) and [issues](https://github.com/BOYSABIO/muttmetrics/issues)  
**Product framing:** [`docs/VISION.md`](docs/VISION.md) (goals, non-goals, later ambition)

## Layout

```
docs/VISION.md     # product vision (public)
docs/adr/          # architecture decisions
src/muttmetrics/   # package
tests/
```

## Setup

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -e ".[dev]"
pytest
ruff check .
ruff format --check .
```

More detail: [`CONTRIBUTING.md`](./CONTRIBUTING.md). Schema work starts in milestone **M1**.

## Privacy

Owner PII and dog photos are sensitive. Do not commit production dumps or real client CSVs. Use synthetic fixtures in CI.

## License

MIT — [`LICENSE`](./LICENSE)
