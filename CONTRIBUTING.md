# Contributing / local development

This is a learning project built production-style: small issues, migrations for schema, CI green before merge.

## Workflow

1. Pick an open issue under the current milestone (start with **M1** after foundation).
2. Branch from `main`: `feat/<issue-number>-short-slug` or `chore/...`.
3. Keep PRs small enough to review in one sitting.
4. Do not commit `.env`, real client CSVs, or DB dumps.

## Tooling

| Tool | Role |
|------|------|
| `ruff` | lint + format |
| `pytest` | tests |
| SQLAlchemy + Alembic | models + migrations (M1+) |
| FastAPI | thin capture/predict API (M3+) |

```bash
pip install -e ".[dev]"
ruff check .
ruff format .
pytest
```

## Design source of truth

Product intent for day-to-day work lives in **GitHub issues/milestones**. The long-form design doc `about.md` is local-only (gitignored) and may be more detailed than what belongs in public. If an issue and `about.md` disagree, update the issue or open an ADR — do not silently invent a third model.

## Issues

GitHub issues are the task list. Do not maintain a parallel local backlog.
