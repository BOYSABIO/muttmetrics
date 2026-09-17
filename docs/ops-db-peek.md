# Ops: local DB peek

How Spencer (or any clone) **sees capture data** without a dashboard. SQL against local Docker Postgres is enough for M3.

Schema reference: [`schema.md`](./schema.md). Connection values match [`docker-compose.yml`](../docker-compose.yml) and [`.env.example`](../.env.example).

## Connection truth

| Param | Value | Notes |
|-------|--------|--------|
| **Host / server name** | `localhost` | Hostname where Postgres listens — **not** the database name |
| Port | `5432` | |
| User | `muttmetrics` | |
| Password | `muttmetrics` | Local only; never use this pattern in production |
| **Database** | `muttmetrics` | Separate field from host |
| SSL | off | Local Docker |

**Footgun:** In the Microsoft PostgreSQL / similar editor extensions, **Server name** = `localhost`. Putting `muttmetrics` there is wrong — that value belongs in the **Database** field.

`DATABASE_URL` in `.env` is the same idea in one string:

```text
postgresql+psycopg://muttmetrics:muttmetrics@localhost:5432/muttmetrics
```

## Connect from the editor (primary)

1. Start Postgres: `docker compose up -d` (wait until healthy).
2. In Cursor/VS Code, open the PostgreSQL extension connection UI.
3. Fill host `localhost`, port `5432`, user/password/database as above; SSL disabled.
4. Connect, then open a SQL editor against database `muttmetrics`.

You should see tables such as `owner`, `dog`, `visit`, `breed`, `service` (after `alembic upgrade head`).

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

One-shot from the host (PowerShell):

```powershell
docker compose exec -T db psql -U muttmetrics -d muttmetrics -c "SELECT COUNT(*) FROM visit;"
```

## Where SQL scripts live

| Kind | Location |
|------|----------|
| Shared / reusable (peek, cleanup, enrichment) | Repo: [`scripts/SQL/`](../scripts/SQL/) — commit these |
| Personal one-offs | Editor scratch, or `scripts/*.local.sql` (gitignored) |
| Real client dumps / PII | Never commit — see Privacy in README |

The extension is a **runner**, not the source of truth. Durable SQL belongs in git.

## Starter queries

Copy-paste into the extension SQL editor or `psql`.

### 1. Counts

```sql
SELECT
  (SELECT COUNT(*) FROM owner) AS owners,
  (SELECT COUNT(*) FROM dog) AS dogs,
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
JOIN dog d ON d.dog_id = v.dog_id
JOIN owner o ON o.owner_id = v.owner_id
ORDER BY v.visit_id DESC
LIMIT 20;
```

### 3. Likely test / lesson clutter (preview only)

```sql
SELECT o.owner_id, o.name AS owner_name, d.dog_id, d.name AS dog_name
FROM owner o
LEFT JOIN dog d ON d.owner_id = o.owner_id
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

This is **read-only**. To delete synthetic rows safely (preview + FK-ordered deletes, keeps real names like Thomas/Milla), use:

[`scripts/SQL/cleanup_synthetic_clients.sql`](../scripts/SQL/cleanup_synthetic_clients.sql)

## Enrichment (UPDATE after thin capture)

Breed, phone, notes, visit fixes — Spencer’s job, not the SPA. Playbook + recipes:

[`ops-enrichment.md`](./ops-enrichment.md) · [`scripts/SQL/lookup_breeds.sql`](../scripts/SQL/lookup_breeds.sql) · [`enrich_dog_breed.sql`](../scripts/SQL/enrich_dog_breed.sql) · [`update_visit.sql`](../scripts/SQL/update_visit.sql) · …

## Pytest writes to this same database

Local `pytest` uses `TestClient` against FastAPI, which **commits** owners/dogs/visits into the compose DB (`localhost:5432/muttmetrics`). Unique UUID names avoid collisions with real clients; they do **not** auto-clean.

CI is different: ephemeral Postgres service container, thrown away after the job.

After heavy local test runs, either run the cleanup script above or wipe (below).

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
