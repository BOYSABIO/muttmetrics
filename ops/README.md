# Ops map

Maintainer tooling for local salon ops. **Product code** lives under `src/muttmetrics/` and `frontend/`.

Layout ([#125](https://github.com/BOYSABIO/muttmetrics/issues/125)): this tree used to be `scripts/`. Package CLIs (`duration_range`, seed, API) stay under `src/muttmetrics/` — they are product scoring/runtime, not dump/purge.

Index of all docs: [`docs/README.md`](../docs/README.md).  
Data-filling policy (thin capture vs enrichment): [`docs/prior.md`](../docs/prior.md) § “How we fill data” (#127).

| Kind | Where | How to run |
|------|--------|------------|
| **Python ops** | `ops/*.py` | `python ops/<name>.py` (venv on, from repo root) |
| **SQL recipes** | `ops/sql/*.sql` | Postgres extension, or PowerShell pipe into `docker compose exec -T db psql` (see each file header) |
| **Package CLIs** | `src/muttmetrics/` | `python -m muttmetrics.<module>` or console scripts from `pyproject.toml` |

Personal / PII-named SQL: `*.local.sql` under `ops/` (gitignored) — never commit real client names.

## Python ops

| Script | Use when | Runbook |
|--------|----------|---------|
| [`backup.py`](./backup.py) | Dump DB (+ photo copy) | [`backup.md`](../docs/runbooks/backup.md) |
| [`backup_check.py`](./backup_check.py) | Staleness check (non-zero if stale) | same |
| [`photo_purge.py`](./photo_purge.py) | Delete a client's photo **files then rows** (dry run default) | [`photos.md`](../docs/runbooks/photos.md) |
| [`photo_sweep.py`](./photo_sweep.py) | Orphan files under `PHOTO_ROOT` with no DB row | same |

## SQL recipes (`ops/sql/`)

Enrichment: prefer SPA **Directory**; SQL below is the escape hatch — [`docs/runbooks/enrichment.md`](../docs/runbooks/enrichment.md). Connection / peek: [`db-peek.md`](../docs/runbooks/db-peek.md).

| File | Use when | More |
|------|----------|------|
| [`compliance_week.sql`](./sql/compliance_week.sql) | Weekly capture numerator | [`compliance.md`](../docs/runbooks/compliance.md) |
| [`calibration_error.sql`](./sql/calibration_error.sql) | Predicted vs actual | [`prior.md`](../docs/prior.md) |
| [`lookup_breeds.sql`](./sql/lookup_breeds.sql) | List breed catalog | enrichment |
| [`enrich_dog_breed.sql`](./sql/enrich_dog_breed.sql) | Set `dog.breed_id` | enrichment |
| [`update_owner.sql`](./sql/update_owner.sql) | Enrich owner contact / notes | enrichment |
| [`update_dog.sql`](./sql/update_dog.sql) | Enrich dog coat / handling / weight | enrichment |
| [`update_visit.sql`](./sql/update_visit.sql) | Fix visit event facts (`condition_score`: 0 worst … 5 best) | enrichment |
| [`first_visit.sql`](./sql/first_visit.sql) | Skeleton insert chain (owner → dog → visit) — wipe carefully | — |
| [`pytest_values_check.sql`](./sql/pytest_values_check.sql) | Spot synthetic pytest owners/dogs | [`db-peek.md`](../docs/runbooks/db-peek.md) |

Cleanup of synthetic clients: `ops/sql/cleanup_synthetic_clients.local.sql` (local only; gitignored when matched). Preview with `ROLLBACK`, then `COMMIT` when sure — see file header. Real photo files: `photo_purge.py` before deleting rows.

## Package CLIs

| Command | Use when | More |
|---------|----------|------|
| `python -m muttmetrics.priors --dog-id N` | Preview P50/P90 without creating a visit | [`prior.md`](../docs/prior.md) |
| `python -m muttmetrics.seed` | Seed breeds / services | [`CONTRIBUTING.md`](../CONTRIBUTING.md) |
| `muttmetrics-api` / `python -m muttmetrics.api` | Run the API | same |

Same prior logic as `POST /visits`.
