# Scripts map

Maintainer tooling for local ops. **Product code** lives under `src/muttmetrics/` and `frontend/`.

Index of all docs: [`docs/README.md`](../docs/README.md). A larger `ops/` tree layout is deferred ([#125](https://github.com/BOYSABIO/muttmetrics/issues/125)).

| Kind | Where | How to run |
|------|--------|------------|
| **Python ops** | `scripts/*.py` | `python scripts/<name>.py` (venv on, from repo root) |
| **SQL recipes** | `scripts/SQL/*.sql` | Postgres extension, or PowerShell pipe into `docker compose exec -T db psql` (see each file header) |
| **Package CLIs** | `src/muttmetrics/` | `python -m muttmetrics.<module>` or console scripts from `pyproject.toml` |

Personal / PII-named SQL: `*.local.sql` under `scripts/` (gitignored) — never commit real client names.

## Python ops

| Script | Use when | Runbook |
|--------|----------|---------|
| [`backup.py`](./backup.py) | Dump DB (+ photo copy) | [`backup.md`](../docs/runbooks/backup.md) |
| [`backup_check.py`](./backup_check.py) | Staleness check (non-zero if stale) | same |
| [`photo_purge.py`](./photo_purge.py) | Delete a client's photo **files then rows** (dry run default) | [`photos.md`](../docs/runbooks/photos.md) |
| [`photo_sweep.py`](./photo_sweep.py) | Orphan files under `PHOTO_ROOT` with no DB row | same |

## SQL recipes (`scripts/SQL/`)

Full enrichment workflow: [`docs/runbooks/enrichment.md`](../docs/runbooks/enrichment.md). Connection / peek: [`db-peek.md`](../docs/runbooks/db-peek.md).

| File | Use when | More |
|------|----------|------|
| [`compliance_week.sql`](./SQL/compliance_week.sql) | Weekly capture numerator | [`compliance.md`](../docs/runbooks/compliance.md) |
| [`calibration_error.sql`](./SQL/calibration_error.sql) | Predicted vs actual | [`prior.md`](../docs/prior.md) |
| [`lookup_breeds.sql`](./SQL/lookup_breeds.sql) | List breed catalog | enrichment |
| [`enrich_dog_breed.sql`](./SQL/enrich_dog_breed.sql) | Set `dog.breed_id` | enrichment |
| [`update_owner.sql`](./SQL/update_owner.sql) | Enrich owner contact / notes | enrichment |
| [`update_dog.sql`](./SQL/update_dog.sql) | Enrich dog coat / handling / weight | enrichment |
| [`update_visit.sql`](./SQL/update_visit.sql) | Fix visit event facts (`condition_score`: 0 worst … 5 best) | enrichment |
| [`first_visit.sql`](./SQL/first_visit.sql) | Skeleton insert chain (owner → dog → visit) — wipe carefully | — |
| [`pytest_values_check.sql`](./SQL/pytest_values_check.sql) | Spot synthetic pytest owners/dogs | [`db-peek.md`](../docs/runbooks/db-peek.md) |

Cleanup of synthetic clients: `scripts/SQL/cleanup_synthetic_clients.local.sql` (local only; gitignored when matched). Preview with `ROLLBACK`, then `COMMIT` when sure — see file header. Real photo files: `photo_purge.py` before deleting rows.

## Package CLIs

| Command | Use when | More |
|---------|----------|------|
| `python -m muttmetrics.duration_range --dog-id N` | Preview P50/P90 without creating a visit | [`prior.md`](../docs/prior.md) |
| `python -m muttmetrics.seed` | Seed breeds / services | [`CONTRIBUTING.md`](../CONTRIBUTING.md) |
| `muttmetrics-api` / `python -m muttmetrics.api` | Run the API | same |

Same prior logic as `POST /visits`.
