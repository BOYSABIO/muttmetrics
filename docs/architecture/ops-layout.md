# Ops tree layout

**Status:** Accepted · **Date:** 2026-10-07 · **Issue:** [#125](https://github.com/BOYSABIO/muttmetrics/issues/125)

## Decision

Maintainer ops live under repo-root **`ops/`**, not `scripts/`:

```text
ops/
  README.md           # map of all maintainer tooling
  backup.py
  backup_check.py
  photo_purge.py
  photo_sweep.py
  sql/                # committed SQL recipes
src/muttmetrics/      # product package (see below)
```

### Package layout (`src/muttmetrics/`)

```text
api/        # FastAPI routes, schemas, services
models/     # SQLAlchemy tables
db/         # engine / session
seed/       # breed + service reference data
priors/     # rules_prior + duration-range CLI
media/      # photo storage + image processing
config.py
```

Same leaf names under `api/routes/`, `api/schemas/`, and `api/services/` (e.g. `dogs.py`) are intentional — the folder is the namespace.

## Why

- `scripts/` mixed salon ops with a vague “misc” name.
- Product CLIs (`python -m muttmetrics.*`) are **not** ops dumps — they stay in the installable package.
- SQL recipes stay in git next to the Python that maintains the same database.
- Root-level `prior.py` / `images.py` / `storage.py` were grouped so the package root stays small.

## Consequences

- Runbooks, CONTRIBUTING, and tests must say `ops/…` (no `scripts/` paths).
- Local PII SQL: `ops/**/*.local.sql` (gitignored).
- Imports: `muttmetrics.priors`, `muttmetrics.media.images` / `muttmetrics.media.storage`.
- CLI: `python -m muttmetrics.priors` (also `muttmetrics-duration-range`).
