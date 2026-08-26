# MuttMetrics

Duration intelligence for a dog grooming business: structured visit data and P50/P90 duration ranges so the day can be packed against variance — not a booking or CRM system.

**Stack:** Python · Postgres · SQLAlchemy 2.x · Alembic · FastAPI  
**Status:** Scaffold — see [milestones](https://github.com/BOYSABIO/muttmetrics/milestones) and [issues](https://github.com/BOYSABIO/muttmetrics/issues)

## Non-goals

No booking calendar, invoicing, payments, or messaging. Own the dog/visit data and predict how long to block; integrate with scheduling tools later if needed.

## Layout

```
docs/adr/          # architecture decisions
docs/learnings/    # concept notes
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
