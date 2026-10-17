# Ops map

Maintainer tooling for local salon ops. **Product code** lives under `src/muttmetrics/` and `frontend/`.

Layout ([#125](https://github.com/BOYSABIO/muttmetrics/issues/125)): this tree used to be `scripts/`. Package CLIs (`duration_range`, seed, API) stay under `src/muttmetrics/` — they are product scoring/runtime, not dump/purge.

Index of all docs: [`docs/README.md`](../docs/README.md).  
Data-filling policy (thin capture vs enrichment): [`docs/prior.md`](../docs/prior.md) § “How we fill data” (#127).

| Kind | Where | How to run |
|------|--------|------------|
| **Python ops** | `ops/*.py` | `python ops/<name>.py` (venv on, from repo root) |
| **SQL recipes** | `ops/sql/*.sql` | Postgres extension, or **encoding-safe** `docker compose cp` + `psql -f` (see below). Never `Get-Content \| docker …` — PowerShell can turn `€` into `?`. |
| **Package CLIs** | `src/muttmetrics/` | `python -m muttmetrics.<module>` or console scripts from `pyproject.toml` |

Personal / PII-named SQL: `*.local.sql` under `ops/` (gitignored) — never commit real client names.

## Python ops

| Script | Use when | Runbook |
|--------|----------|---------|
| [`backup.py`](./backup.py) | Dump DB (+ photo copy) | [`backup.md`](../docs/runbooks/backup.md) |
| [`backup_check.py`](./backup_check.py) | Staleness check (non-zero if stale) | same |
| [`photo_purge.py`](./photo_purge.py) | Delete a client's photo **files then rows** (dry run default) | [`photos.md`](../docs/runbooks/photos.md) |
| [`photo_sweep.py`](./photo_sweep.py) | Orphan files under `PHOTO_ROOT` with no DB row | same |
| [`backfill_size_band.py`](./backfill_size_band.py) | Set `dog.size_band` from `weight_kg` (#171) | dry-run default; `--apply` to write |

## SQL recipes (`ops/sql/`)

Enrichment: prefer SPA **Directory**; SQL below is the escape hatch — [`docs/runbooks/enrichment.md`](../docs/runbooks/enrichment.md). Connection / peek: [`db-peek.md`](../docs/runbooks/db-peek.md).

### How to run a `.sql` file (encoding-safe)

Do **not** pipe file text through PowerShell into `psql`. Copy the file into the container as bytes, then let `psql` read it:

```powershell
docker compose cp .\ops\sql\compliance_week.sql db:/tmp/q.sql
docker compose exec -T db psql -U muttmetrics -d muttmetrics -f /tmp/q.sql
```

**Why (#154):** during the `scripts` → `ops` move, UTF-8 punctuation in comments was misread as CP437 and saved again (double-encoding / mojibake — e.g. an em dash became a multi-character junk sequence). Separately, `Get-Content | docker …` re-encodes the pipe with `$OutputEncoding` and can silently replace `€` or umlauts. M5 money/metric SQL must not go through that path. Guard: `tests/unit/test_sql_encoding.py` (it looks for the junk signature; do not paste that signature into docs as an “example”).

| File | Use when | More |
|------|----------|------|
| [`compliance_week.sql`](./sql/compliance_week.sql) | Weekly capture numerator | [`compliance.md`](../docs/runbooks/compliance.md) |
| [`metric_eur_per_hour.sql`](./sql/metric_eur_per_hour.sql) | €/hour by condition × shaved (#27) | [`analytics.md`](../docs/runbooks/analytics.md) |
| [`metric_prediction_health.sql`](./sql/metric_prediction_health.sql) | Pivot / overrun / P90 miss range functions (#28, #170) | [`analytics.md`](../docs/runbooks/analytics.md) |
| [`metric_utilization.sql`](./sql/metric_utilization.sql) | Per-day planned vs actual vs buffer (#29) | [`analytics.md`](../docs/runbooks/analytics.md) |
| [`calibration_error.sql`](./sql/calibration_error.sql) | Predicted vs actual (cross-checks the #28 functions) | [`prior.md`](../docs/prior.md) |
| [`lookup_breeds.sql`](./sql/lookup_breeds.sql) | List breed catalog | enrichment |
| [`enrich_dog_breed.sql`](./sql/enrich_dog_breed.sql) | Set `dog.breed_id` | enrichment |
| [`update_owner.sql`](./sql/update_owner.sql) | Enrich owner contact / notes | enrichment |
| [`update_dog.sql`](./sql/update_dog.sql) | Enrich dog coat / handling / weight | enrichment |
| [`update_visit.sql`](./sql/update_visit.sql) | Fix visit event facts (`condition_score`: 0 worst … 5 best) | enrichment |
| [`pytest_values_check.sql`](./sql/pytest_values_check.sql) | Spot synthetic pytest owners/dogs | [`db-peek.md`](../docs/runbooks/db-peek.md) |

Cleanup of synthetic clients: `ops/sql/cleanup_synthetic_clients.local.sql` (local only; gitignored when matched). Preview with `ROLLBACK`, then `COMMIT` when sure — see file header. Real photo files: `photo_purge.py` before deleting rows.

## Package CLIs

| Command | Use when | More |
|---------|----------|------|
| `python -m muttmetrics.priors --dog-id N` | Preview P50/P90 without creating a visit | [`prior.md`](../docs/prior.md) |
| `python -m muttmetrics.seed` | Seed breeds / services | [`CONTRIBUTING.md`](../CONTRIBUTING.md) |
| `muttmetrics-api` / `python -m muttmetrics.api` | Run the API | same |

Same prior logic as `POST /visits`.
