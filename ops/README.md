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

## What this folder is (and is not)

- **Nothing here is imported by the API or SPA.** Product reads/writes go through FastAPI and Directory. `ops/` is for you at the laptop: backups, photo cleanup, synthetic demos, and SQL you open by hand.
- **SQL files are recipes, not jobs.** They are never scheduled. Copy/open them when a runbook says so. Deleting one only removes the documented peek — the real metric logic lives in Postgres functions / Python.
- **Directory first for enrichment.** Prefer Clients in the SPA for one-off pet/owner/visit edits. The `update_*.sql` / `enrich_*.sql` recipes are the escape hatch (bulk, API down, offline).
- **“Ran once” ≠ delete.** `backfill_size_band.py` was first used for the #171 go-live, but it stays: Directory only write-throughs `size_band` when weight changes **in the app**. SQL weight edits, species/band rule changes (e.g. cat kg cutoffs after the groomer confirms), and restores still need a recompute. Dry-run is the default.

Do **not** merge purge+sweep, backup+check, or the metric SQL files into one mega-script — each answers a different failure mode.

## Python ops

| Script | Use when | Runbook |
|--------|----------|---------|
| [`backup.py`](./backup.py) | Dump DB (+ additive photo copy) | [`backup.md`](../docs/runbooks/backup.md) |
| [`backup_check.py`](./backup_check.py) | Staleness check (non-zero if stale) — pair with backup, not a duplicate | same |
| [`photo_purge.py`](./photo_purge.py) | Delete a client's photo **files then rows** (dry run default) | [`photos.md`](../docs/runbooks/photos.md) |
| [`photo_sweep.py`](./photo_sweep.py) | Orphan **files** under `PHOTO_ROOT` with no DB row (opposite of purge) | same |
| [`backfill_size_band.py`](./backfill_size_band.py) | Recompute `pet.size_band` from `weight_kg` + `species` (#171 / #190) | dry-run default; `--apply` to write |
| [`client_export.py`](./client_export.py) | Art. 15: export one owner → `data/exports/` (#195) | [`client-requests.md`](../docs/runbooks/client-requests.md) |
| [`client_erase.py`](./client_erase.py) | Art. 17: anonymise one owner (photos + PII scrub; keep visit facts) (#195) | dry-run default; `--apply`; same runbook |
| [`deploy.py`](./deploy.py) | Release deploy: backup → pull → migrate → SPA build → health (#197) | [`release.md`](../docs/runbooks/release.md); `--dry-run` |
| [`demo_data.py`](./demo_data.py) | Load Syn* fixtures into an **empty** DB (demos, screenshots, Playwright e2e) | refuses if any visit exists; CI calls it |

## SQL recipes (`ops/sql/`)

Enrichment escape hatch: [`docs/runbooks/enrichment.md`](../docs/runbooks/enrichment.md). Connection / peek: [`db-peek.md`](../docs/runbooks/db-peek.md).

### How to run a `.sql` file (encoding-safe)

Do **not** pipe file text through PowerShell into `psql`. Copy the file into the container as bytes, then let `psql` read it:

```powershell
docker compose cp .\ops\sql\compliance_week.sql db:/tmp/q.sql
docker compose exec -T db psql -U muttmetrics -d muttmetrics -f /tmp/q.sql
```

**Why (#154):** during the `scripts` → `ops` move, UTF-8 punctuation in comments was misread as CP437 and saved again (double-encoding / mojibake — e.g. an em dash became a multi-character junk sequence). Separately, `Get-Content | docker …` re-encodes the pipe with `$OutputEncoding` and can silently replace `€` or umlauts. M5 money/metric SQL must not go through that path. Guard: `tests/unit/test_sql_encoding.py` (it looks for the junk signature; do not paste that signature into docs as an “example”).

### Metric / compliance peeks

These call the same Postgres **functions** the API uses (ADR-003). Edit the date literals; they are not a second formula. `calibration_error.sql` is the breed/condition slice of the same overrun/P90 ideas as `metric_prediction_health.sql` — keep both.

| File | Use when | More |
|------|----------|------|
| [`compliance_week.sql`](./sql/compliance_week.sql) | Weekly capture numerator (denom is manual) | [`compliance.md`](../docs/runbooks/compliance.md) |
| [`metric_eur_per_hour.sql`](./sql/metric_eur_per_hour.sql) | €/hour by condition × shaved (#27) | [`analytics.md`](../docs/runbooks/analytics.md) |
| [`metric_prediction_health.sql`](./sql/metric_prediction_health.sql) | Pivot / overrun / P90 miss for a date range (#28, #170) | [`analytics.md`](../docs/runbooks/analytics.md) |
| [`metric_utilization.sql`](./sql/metric_utilization.sql) | Per-day planned vs actual vs buffer (#29) | [`analytics.md`](../docs/runbooks/analytics.md) |
| [`calibration_error.sql`](./sql/calibration_error.sql) | Predicted vs actual **by breed / condition** (cross-checks #28) | [`prior.md`](../docs/prior.md) |

### Enrichment escape hatch

Prefer Directory for one-offs. Open these for bulk / offline / API-down work.

| File | Use when | More |
|------|----------|------|
| [`lookup_breeds.sql`](./sql/lookup_breeds.sql) | List breed catalog (`species`, timings) | enrichment |
| [`enrich_pet_breed.sql`](./sql/enrich_pet_breed.sql) | Set `pet.breed_id` (+ secondary) | enrichment |
| [`update_owner.sql`](./sql/update_owner.sql) | Enrich owner contact / notes | enrichment |
| [`update_pet.sql`](./sql/update_pet.sql) | Enrich pet coat / handling / weight | enrichment |
| [`update_visit.sql`](./sql/update_visit.sql) | Fix visit event facts (`condition_score`: 0 worst … 5 best) | enrichment |

Cleanup of synthetic clients: `ops/sql/cleanup_synthetic_clients.local.sql` (local only; gitignored when matched). Preview with `ROLLBACK`, then `COMMIT` when sure — see file header. Real photo files: `photo_purge.py` before deleting rows.

## Package CLIs

| Command | Use when | More |
|---------|----------|------|
| `python -m muttmetrics.priors --pet-id N` | Preview P50/P90 without creating a visit | [`prior.md`](../docs/prior.md) |
| `python -m muttmetrics.seed` | Seed breeds / services | [`CONTRIBUTING.md`](../CONTRIBUTING.md) |
| `muttmetrics-api` / `python -m muttmetrics.api` | Run the API | same |

Same prior logic as `POST /visits`.
