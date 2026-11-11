# Ops: local DB peek

How Owner (or any clone) **sees capture data** without a dashboard. SQL against local Docker Postgres is enough for M3.

Schema reference: [`schema.md`](../architecture/schema.md). Connection values match [`docker-compose.yml`](../../docker-compose.yml) and [`.env.example`](../../.env.example).

## Connection truth

| Param | Value | Notes |
|-------|--------|--------|
| **Host / server name** | `localhost` | Hostname where Postgres listens — **not** the database name |
| Port | `5432` | |
| User | `muttmetrics` | |
| Password | `POSTGRES_PASSWORD` in `.env` | Set when the volume is first created (see below) |
| **Database** | `muttmetrics` | Separate field from host |
| SSL | off | Local Docker |

**Footgun:** In the Microsoft PostgreSQL / similar editor extensions, **Server name** = `localhost`. Putting `muttmetrics` there is wrong — that value belongs in the **Database** field.

`DATABASE_URL` in `.env` is the same idea in one string:

```text
postgresql+psycopg://muttmetrics:<POSTGRES_PASSWORD>@localhost:5432/muttmetrics
```

**Changing the password later.** Postgres only reads `POSTGRES_PASSWORD` when the volume is first created. To change it on an existing database, set the new value in the database first, then in `.env` (both `POSTGRES_PASSWORD` and the password inside `DATABASE_URL`), then restart the API:

```bash
docker compose exec db psql -U muttmetrics -d muttmetrics -c "ALTER USER muttmetrics PASSWORD '<new>';"
```

## Connect from the editor (primary)

1. Start Postgres: `docker compose up -d` (wait until healthy).
2. In Cursor/VS Code, open the PostgreSQL extension connection UI.
3. Fill host `localhost`, port `5432`, user/password/database as above; SSL disabled.
4. Connect, then open a SQL editor against database `muttmetrics`.

You should see tables such as `owner`, `pet`, `visit`, `breed`, `service` (after `alembic upgrade head`).

## Connect with `psql` (secondary)

From the repo root (Docker must be up):

```bash
docker compose exec db psql -U muttmetrics -d muttmetrics
```

Useful once inside:

```text
\dt          -- list tables
\d visit     -- describe visit columns
\q           -- quit
```

One-shot from the host (PowerShell) — ASCII-only `-c` strings are fine:

```powershell
docker compose exec -T db psql -U muttmetrics -d muttmetrics -c "SELECT COUNT(*) FROM visit;"
```

### Encoding-safe: run a `.sql` file

For any script that may contain non-ASCII (euro, dashes, German breed names), **copy the file into the container**, then `-f`. Do not `Get-Content | docker compose exec …` — Windows PowerShell re-encodes the pipe and can turn `€` into `?` with no error ([#154](https://github.com/BOYSABIO/muttmetrics/issues/154)).

```powershell
docker compose cp .\ops\sql\compliance_week.sql db:/tmp/q.sql
docker compose exec -T db psql -U muttmetrics -d muttmetrics -f /tmp/q.sql
```

**Root cause note (M5 / #154):** during the `scripts` → `ops` relocate (#125), several recipe comments were double-encoded (UTF-8 bytes misread as CP437, then saved as UTF-8 again). Queries were intact; comments were poisoned. Files were repaired by reversing that round-trip. `tests/unit/test_sql_encoding.py` fails if the mojibake signature returns — describe it in prose, do not embed the junk characters in docs.

## Where SQL scripts live

Full map (Python ops + SQL + package CLIs): [`ops/README.md`](../../ops/README.md).

| Kind | Location |
|------|----------|
| Shared / reusable (peek, cleanup, enrichment, compliance, calibration) | Repo: [`ops/sql/`](../../ops/sql/) — commit these |
| Personal one-offs | Editor scratch, or `ops/**/*.local.sql` (gitignored) |
| Real client dumps / PII | Never commit — see Privacy in README |

The extension is a **runner**, not the source of truth. Durable SQL belongs in git.

## Starter queries

Copy-paste into the extension SQL editor or `psql`.

### 1. Counts

```sql
SELECT
  (SELECT COUNT(*) FROM owner) AS owners,
  (SELECT COUNT(*) FROM pet) AS pets,
  (SELECT COUNT(*) FROM visit) AS visits;
```

### 2. Last 20 visits (dog + owner names)

```sql
SELECT
  v.visit_id,
  v.visit_date,
  v.actual_minutes,
  v.status,
  d.name AS dog_name,
  o.name AS owner_name
FROM visit v
JOIN pet d ON d.pet_id = v.pet_id
JOIN owner o ON o.owner_id = v.owner_id
ORDER BY v.visit_id DESC
LIMIT 20;
```

### 3. Likely test / lesson clutter (preview only)

```sql
SELECT o.owner_id, o.name AS owner_name, d.pet_id, d.name AS dog_name
FROM owner o
LEFT JOIN pet d ON d.owner_id = o.owner_id
WHERE o.name ILIKE '%Capture%'
   OR o.name ILIKE '%Lesson%'
   OR o.name ILIKE 'Test Owner%'
   OR o.name ILIKE 'Flow Owner%'
   OR d.name ILIKE '%Capture%'
   OR d.name ILIKE 'BrowseDog%'
   OR d.name ILIKE 'Test Dog%'
   OR d.name ~* '^Bella[ 0-9a-f]{4,}$'
ORDER BY o.name, d.name;
```

This is **read-only**. Since [#222](https://github.com/BOYSABIO/muttmetrics/issues/222) (2026-11-11) the dev database holds synthetic data only, so a stray test row there needs no surgery: recreate the dev DB (`docker compose down -v`, then the setup in CONTRIBUTING). Real data is looked at on the box only, read-only ([`home-server.md`](./home-server.md)).

## Enrichment (UPDATE after thin capture)

Breed, phone, notes, visit fixes — Owner’s job, not the SPA. Playbook + recipes:

[`ops-enrichment.md`](./enrichment.md) · [`ops/sql/lookup_breeds.sql`](../../ops/sql/lookup_breeds.sql) · [`enrich_pet_breed.sql`](../../ops/sql/enrich_pet_breed.sql) · [`update_visit.sql`](../../ops/sql/update_visit.sql) · …

## Pytest and this database

Tests never touch this database: they run on `muttmetrics_test` and refuse anything else (#177, setup in CONTRIBUTING). Synthetic owners like `Test Owner` / `Flow Owner` in an old dev DB were leftovers from before that; the dev DB was recreated from `ops/demo_data.py` in #222.

## Nuclear wipe (local only)

Destroys **all** local DB data (including real trial visits):

```bash
docker compose down -v
docker compose up -d
# wait until healthy
alembic upgrade head
python -m muttmetrics.seed
```

## Out of scope here

- Read-only web admin UI  
- M5 product dashboards  
- Production / Neon peek (different credentials; never paste into this doc)  
