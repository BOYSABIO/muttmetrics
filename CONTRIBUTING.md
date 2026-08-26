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
| `pre-commit` | runs ruff on `git commit` before the commit is created |
| `pytest` | tests |
| SQLAlchemy + Alembic | models + migrations (M1+) |
| FastAPI | thin capture/predict API (M3+) |

```bash
pip install -e ".[dev]"
pre-commit install          # once per clone — installs the git hook
pre-commit run --all-files  # optional: check everything now
ruff check .
ruff format .               # apply
ruff format --check .       # CI uses this (fails if unformatted)
pytest
```

After `pre-commit install`, each `git commit` runs ruff lint (with autofix) and ruff format on staged files. If something was fixed, stage again and recommit. CI still runs the same checks as the backstop.

## Design source of truth

Product intent for day-to-day work lives in **GitHub issues/milestones**. Public framing (goals, non-goals, later ambition) is [`docs/VISION.md`](./docs/VISION.md). Deep local design notes may exist off-repo; if an issue and VISION disagree on boundaries, update the issue or open an ADR — do not silently invent a third model.

## Issues

GitHub issues are the task list. Do not maintain a parallel local backlog.
