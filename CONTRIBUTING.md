# Contributing / local development

This is a learning project built production-style: small issues, migrations for schema, CI green before merge.

## Workflow

1. Pick an open issue under the current milestone (see [milestones](https://github.com/BOYSABIO/muttmetrics/milestones)).
2. Branch from `main`: `feat/<issue-number>-short-slug` or `chore/...`.
3. Keep PRs small enough to review in one sitting.
4. Do not commit `.env`, real client CSVs, or DB dumps.

## Tooling

| Tool | Role |
|------|------|
| `ruff` | lint + format |
| `pre-commit` | runs ruff on `git commit` before the commit is created |
| `pytest` | tests |
| Playwright | end-to-end smoke in `frontend/e2e/` (#196) |
| `pip-audit` / `npm audit` | dependency vulns in CI (#196) |
| SQLAlchemy + Alembic | models + migrations (M1+) |
| FastAPI | thin capture/predict API (M3+) |
| `.gitattributes` | LF in repo — stops Windows CRLF whole-file diff noise |

```bash
pip install -e ".[dev]"
pre-commit install          # once per clone — installs the git hook
pre-commit run --all-files  # optional: check everything now
ruff check .
ruff format .               # apply
ruff format --check .       # CI uses this (fails if unformatted)
pytest
```

Test layout: `tests/api/` (HTTP + DB), `tests/db/` (SQL metric functions and the rollback scratchpad, no HTTP), `tests/unit/` (no Postgres), `tests/fixtures/` (synthetic metric week/month data + loaders). Shared fixtures live in `tests/conftest.py` (`client`, `db_session`, `auth_headers`, `metric_week`). API/`db_session` tests share one connection per test and **roll back** when the test ends — see [`docs/runbooks/db-peek.md`](./docs/runbooks/db-peek.md). Prefer `127.0.0.1` over `localhost` on Windows.

**Tests use their own database** (#177). `pytest` points every run at `muttmetrics_test` and stops before collecting anything if the database name does not contain `test`, so a stray `DATABASE_URL` can never aim tests at the real salon data. Override with `TEST_DATABASE_URL`. One-time setup (and again after any new migration):

```powershell
docker compose exec db createdb -U muttmetrics muttmetrics_test   # once
$env:DATABASE_URL = "postgresql+psycopg://muttmetrics:muttmetrics@127.0.0.1:5432/muttmetrics_test"
alembic upgrade head
python -m muttmetrics.seed
Remove-Item Env:DATABASE_URL                                      # back to your .env
pytest
```

After `pre-commit install`, each `git commit` runs ruff lint (with autofix) and ruff format on staged files. If something was fixed, stage again and recommit. CI still runs the same checks as the backstop.

## End-to-end smoke (#196)

CI runs Playwright against a **real** API + Postgres (`e2e` job in [`.github/workflows/ci.yml`](./.github/workflows/ci.yml)): capture save, dashboard fixture week, Directory edit. Unit/API tests stay in `pytest`; these three flows only check that the pieces still fit together.

**Locally** (throwaway DB only — never the salon database):

```powershell
docker compose exec db createdb -U muttmetrics muttmetrics_e2e   # once
$env:DATABASE_URL = "postgresql+psycopg://muttmetrics:muttmetrics@127.0.0.1:5432/muttmetrics_e2e"
# ≥24 chars; must match frontend/.env VITE_API_KEY (not the .env.example placeholder — #187)
$env:API_KEY = "local-e2e-key-not-for-production"
alembic upgrade head
python -m muttmetrics.seed
python ops/demo_data.py          # first time only (refuses if visits exist)
muttmetrics-api                  # terminal 1 — leave running
```

```powershell
cd frontend
npm run build
npm run e2e                      # starts preview on :5174 if needed
```

Synthetic Syn* rows only (`ops/demo_data.py`) — never a dump. First-time browsers: `npx playwright install chromium` in `frontend/`.

## Dependabot (#196)

Weekly grouped PRs for pip, npm (`/frontend`), and github-actions (see [`.github/dependabot.yml`](./.github/dependabot.yml)). **CI green → merge.** Major bumps: read the changelog first. Every PR also runs `pip-audit` and `npm audit --audit-level=high`.

## Local Postgres (Docker Compose)

**Primary dev path** — offline, reproducible, matches credentials in `.env.example`.

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) running.

```bash
cp .env.example .env          # Windows: copy .env.example .env
docker compose up -d          # start db service
docker compose ps             # wait for STATUS (healthy)
alembic upgrade head          # create tables
```

Verify:

```bash
docker compose exec db psql -U muttmetrics -d muttmetrics -c "\dt"
```

Postgres is published on `127.0.0.1:5432` only (see `ports:` in `docker-compose.yml`) — reachable from this machine, never from the LAN or the tailnet. `DATABASE_URL` uses `127.0.0.1`, not `localhost`: on Windows `localhost` can resolve to IPv6 `::1` first and stall every new connection for ~a minute.

Day-to-day:

```bash
docker compose stop           # stop, keep data
docker compose down           # remove container, keep volume
docker compose down -v        # wipe data — then alembic upgrade head again
docker compose logs db        # debug startup
```

If port 5432 is in use, stop any old `muttmetrics-pg` container or native Postgres.

### DB peek (editor + starter SQL)

To inspect capture rows without a dashboard: connect the PostgreSQL extension or `psql`, then run the starter SELECTs in [`docs/runbooks/db-peek.md`](./docs/runbooks/db-peek.md). That doc also covers the host-vs-database footgun, pytest clutter, and wipe/cleanup.

To enrich dog / owner after thin capture: prefer the SPA **Directory** tab; SQL recipes are the escape hatch (visit fact fixes, bulk). Playbook: [`docs/runbooks/enrichment.md`](./docs/runbooks/enrichment.md).

**Where does new code go?** ([#180](https://github.com/BOYSABIO/muttmetrics/issues/180))

| It… | Put it in |
|---|---|
| parses a request or shapes a response | `api/routes/` + `api/schemas/` (routes stay thin) |
| queries or writes the DB for one API feature | `api/services/` |
| is needed by a route **and** a CLI or ops script | `muttmetrics/services/` (no FastAPI imports, raises `LookupError` / `ValueError`) |
| is a pure rule with no DB | its domain package, e.g. `priors/` |

Nothing outside `muttmetrics.api` may import from it; `tests/unit/test_layering.py` enforces that. Routes map `LookupError` → 404 and `ValueError` → 422.

**Where is ops tool X?** See [`ops/README.md`](./ops/README.md) — backups/photos (Python), SQL recipes, and package CLIs (`python -m muttmetrics.priors`, seed). Layout: [`docs/architecture/ops-layout.md`](./docs/architecture/ops-layout.md).

### Alternative: Neon (hosted)

For a shared or staging database later — not required for local dev.

1. Create a free project at [neon.tech](https://neon.tech).
2. Copy the **pooled** Postgres connection string.
3. Convert to SQLAlchemy/psycopg format in `.env`:

   ```env
   DATABASE_URL=postgresql+psycopg://user:pass@ep-....neon.tech/neondb?sslmode=require
   ```

4. Run `alembic upgrade head` against that URL (same migrations, different host).

Do not commit Neon URLs or passwords. Keep `.env` gitignored.

## Database and migrations

Schema is defined in SQLAlchemy models (`src/muttmetrics/models/`) and applied with [Alembic](https://alembic.sqlalchemy.org/). See [`docs/architecture/schema.md`](./docs/architecture/schema.md) for the entity diagram.

**Prerequisites:** `.env` from `.env.example` and Postgres running (see **Local Postgres** above).

```bash
# Apply all migrations (fresh clone or after pull)
alembic upgrade head

# See current revision
alembic current

# See migration history
alembic history

# Roll back one migration
alembic downgrade -1

# Roll back everything (empty schema)
alembic downgrade base
```

**Changing the schema:** edit models → autogenerate → **read the draft** → dump → upgrade.

```bash
alembic revision --autogenerate -m "describe change"
# Review alembic/versions/<rev>_describe_change.py — autogenerate is a DRAFT
python ops/backup.py        # first, on any database that holds real rows
alembic upgrade head
```

Autogenerate diffs two schema *states*; it does not know what you *meant*. A rename comes out as `drop_column` + `add_column`, a type change can silently round every value, and CI catches neither because it migrates an **empty** database. [`docs/runbooks/migrations.md`](./docs/runbooks/migrations.md) has the shapes to look for, expand/migrate/contract, and `alembic stamp`.

`tests/unit/test_migration_safety.py` fails any migration whose `upgrade()` drops something without an acknowledgement line (runbook §4). CI (`.github/workflows/ci.yml`) runs ruff, migrations, seed, pytest, frontend lint/build, `pip-audit` / `npm audit`, and the Playwright `e2e` job (#196).

## Backups (#95)

`ops/backup.py` writes a `pg_dump -Fc` archive plus an **additive** photo copy under `BACKUP_ROOT` (outside the repo); `ops/backup_check.py` reports how stale the last run is and exits non-zero when it is too old. Retention: 14 daily dumps, Sundays for 8 weeks, photos never auto-pruned.

Run it by hand for now — **scheduling is documented but not enabled yet** ([`docs/runbooks/backup.md`](./docs/runbooks/backup.md) §4). Everything about restoring, including the drill that proves a dump is real, is in that runbook.

```bash
python ops/backup.py
python ops/backup_check.py
```

## Capture photos (#30)

Photo **bytes** live on disk under `PHOTO_ROOT`, deliberately **outside the repo**; photo **metadata** lives in the `photo` table. Rationale: [ADR-002](./docs/architecture/adr/002-photo-storage.md). Operations: [`docs/runbooks/photos.md`](./docs/runbooks/photos.md). Privacy: [`docs/architecture/privacy.md`](./docs/architecture/privacy.md).

```env
PHOTO_ROOT=C:/muttmetrics-data/photos   # optional; defaults to ~/muttmetrics-data/photos
```

| Piece | Role |
|-------|------|
| `src/muttmetrics/media/storage.py` | keys ↔ files: key generation, atomic write, read, delete, traversal checks |
| `src/muttmetrics/media/images.py` | bytes ↔ bytes: decode, EXIF strip, downscale, re-encode JPEG |
| `src/muttmetrics/api/routes/photos.py` | upload / list / serve |
| `photo` table | `dog_id`, optional `visit_id`, `kind`, relative `storage_key`, size, sha256, `created_at` |
| `ops/photo_purge.py` | delete a client's photos (files first, then rows) — dry run by default |
| `ops/photo_sweep.py` | find files with no row (crash leftovers) — dry run by default |

Deps: `pillow` (decode/encode), `pillow-heif` (iPhone HEIC), `python-multipart` (upload bodies).

**Rules worth not relearning the hard way:** the database stores a *relative* key, so moving the host is a config change; the file is written **before** the row, because an orphan file is removable litter while a row without its file is a broken promise; foreign keys have no `ON DELETE CASCADE`, because Postgres cannot delete files and a cascade would strand them.

Visit photos live only in the `photo` table — the old `visit.*_photos` URL arrays were dropped in [#98](https://github.com/BOYSABIO/muttmetrics/issues/98).

## Seed reference data

After migrations, load breed priors and the service catalog (idempotent — safe to re-run):

```bash
python -m muttmetrics.seed
```

Timing priors live in `src/muttmetrics/seed/data.py`. Catalog floors (`service.price_base`) are optional and **never committed** — copy [`data/pricing.example.json`](./data/pricing.example.json) to `data/private/pricing.json` (gitignored) and fill in real numbers. CI and any clone without that file seed `price_base` as NULL, which is valid. Re-running seed without the private file will null out previously seeded prices. On-the-spot charge still lives on `visit.quoted_price` / `final_price` / `tip`.

## Running the API

The HTTP app lives in `src/muttmetrics/api/`. Preferred local start (safe reload defaults):

```bash
python -m muttmetrics.api
# equivalent after pip install -e .: muttmetrics-api
```

That runs uvicorn with `--reload` scoped to `src/` so WatchFiles does **not** watch `.venv` (which can hang on Windows).

Raw uvicorn if you need custom flags:

```bash
uvicorn muttmetrics.api.app:app --reload --reload-dir src --host 127.0.0.1 --port 8000
```

| URL | Who | What |
|-----|-----|------|
| `http://127.0.0.1:8000/health` | Ops / smoke | Liveness JSON — **public**, no API key, no Postgres |
| `http://127.0.0.1:8000/ping` | maintainer smoke | Auth check — requires `X-API-Key` |
| `http://127.0.0.1:8000/owners` | Onboarding | `GET` search (`?q=`); `POST` create / phone-match reuse / **409** on name clash ([#187](https://github.com/BOYSABIO/muttmetrics/issues/187), [#191](https://github.com/BOYSABIO/muttmetrics/issues/191)) |
| `http://127.0.0.1:8000/owners/{id}` | Directory | `GET` owner profile; `PATCH` safe fields ([#131](https://github.com/BOYSABIO/muttmetrics/issues/131), [#132](https://github.com/BOYSABIO/muttmetrics/issues/132)) |
| `http://127.0.0.1:8000/dogs` | Onboarding / directory | `POST` create-or-get; `GET` list/search (`?q=`) with `owner_name` |
| `http://127.0.0.1:8000/dogs/{id}` | Directory | `GET` dog profile; `PATCH` safe fields (writes `size_band` from weight, [#171](https://github.com/BOYSABIO/muttmetrics/issues/171)) |
| `http://127.0.0.1:8000/dogs/{id}/duration-range` | maintainer | `GET` preview of the P50/P90 estimate without creating a visit ([#26](https://github.com/BOYSABIO/muttmetrics/issues/26)); not used by the SPA yet |
| `http://127.0.0.1:8000/dogs/{id}/photos` | Directory | `POST` profile photo upload |
| `http://127.0.0.1:8000/breeds` | Directory | `GET` breed catalog for the breed picker ([#151](https://github.com/BOYSABIO/muttmetrics/issues/151)) |
| `http://127.0.0.1:8000/services` | Capture | `GET` seeded package catalog for the SPA picker ([#110](https://github.com/BOYSABIO/muttmetrics/issues/110)) |
| `http://127.0.0.1:8000/add-ons` | Capture | `GET` seeded technique / add-on catalog ([#192](https://github.com/BOYSABIO/muttmetrics/issues/192)) |
| `http://127.0.0.1:8000/visits` | Capture | `POST` create visit — requires existing dog/owner ids, and the dog must belong to that owner; optional `add_on_ids` |
| `http://127.0.0.1:8000/visits/{id}/photos` | Capture | `POST` multipart photo upload; `GET` metadata list ([#30](https://github.com/BOYSABIO/muttmetrics/issues/30)) |
| `http://127.0.0.1:8000/photos/{id}` | Capture | `GET` the JPEG bytes (API key required — an `<img src>` cannot fetch it) |
| `http://127.0.0.1:8000/metrics/period` | Dashboard | `GET` any inclusive range up to 366 days (`start`/`end`; week = Mon–Sun, month = calendar month). SPA uses this for both modes ([#170](https://github.com/BOYSABIO/muttmetrics/issues/170), [#187](https://github.com/BOYSABIO/muttmetrics/issues/187)) |
| `http://127.0.0.1:8000/metrics/week` | Ops / curl | Thin Mon–Sun wrapper + `previous_week` ([#156](https://github.com/BOYSABIO/muttmetrics/issues/156)); same payload shape, period bounds are `start`/`end` |
| `http://127.0.0.1:8000/docs` | maintainer | OpenAPI test console — **not** the groomer’s UI |
| `http://127.0.0.1:5173` (dev) / `:5174` (preview) | groomer | React capture SPA in `frontend/` — **only** salon UI ([#69](https://github.com/BOYSABIO/muttmetrics/issues/69)–[#72](https://github.com/BOYSABIO/muttmetrics/issues/72)) |

`GET` / `POST /capture` (old Jinja form) was removed in [#86](https://github.com/BOYSABIO/muttmetrics/issues/86) — expect **404**.

`muttmetrics.api.app:app` means: import module `muttmetrics.api.app`, use variable `app`. That file must sit at `src/muttmetrics/api/app.py` — not under `routes/`.

Stop with `Ctrl+C`.

### API auth (#19)

Protected routes use a shared secret from `.env`:

```http
X-API-Key: <same value as API_KEY in .env>
```

| Piece | Role |
|-------|------|
| `API_KEY` in `.env` | Server-side secret (required; see `.env.example`) |
| Header `X-API-Key` | What callers send |
| `require_api_key` in `src/muttmetrics/api/deps.py` | FastAPI dependency — 401 if missing/wrong |
| Startup check ([#187](https://github.com/BOYSABIO/muttmetrics/issues/187)) | API refuses to start if `API_KEY` is `dev-change-me` or shorter than 24 characters |
| `GET /health` | Stays **public** (no key) |
| Every other route: `/ping`, owners, dogs, breeds, services, visits, metrics | Protected |
| Photo routes (`/visits/{id}/photos`, `/dogs/{id}/photos`, `/photos/{id}`) | Protected — these serve client photos |

All write paths require `X-API-Key`. The unauthenticated Jinja `/capture` form is gone ([#86](https://github.com/BOYSABIO/muttmetrics/issues/86)).

Generate a local key (same value in root `.env` and `frontend/.env` as `VITE_API_KEY`):

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

In `/docs`, use **Authorize** and set `X-API-Key` to your `.env` value before calling protected endpoints.

Quick checks:

```bash
curl.exe -s -w "`nHTTP %{http_code}`n" http://127.0.0.1:8000/health
curl.exe -s -w "`nHTTP %{http_code}`n" -H "X-API-Key: %API_KEY%" http://127.0.0.1:8000/ping
```

Never commit real `.env` values. CI sets `API_KEY` as an environment variable in `.github/workflows/ci.yml`; inside tests, the `client` fixture sets it with `monkeypatch`.

### React capture SPA (#69–#72)

**Only** app UI for groomer/maintainer (not `/docs`). Vite + React + TypeScript in `frontend/`. **All API calls live in `src/api.ts`** (headers, error messages, response types) and shared date helpers in `src/dates.ts` ([#180](https://github.com/BOYSABIO/muttmetrics/issues/180)); components import from there and never call `fetch` themselves. Screens: `App.tsx` is the shell (home vs capture); `ThisWeek.tsx` is the dashboard; `Directory.tsx` is the client list, opening `DogProfileView` / `OwnerProfileView`; `Capture.tsx` is search → new client → 3-step visit wizard (then optional back-to-back dog), with the resumable draft in `draft.ts`. Top areas: **This week** | **Clients** ([#138](https://github.com/BOYSABIO/muttmetrics/issues/138)). Capture modes: **search** → **visit**, or **new** client → **visit**, then **after_save** for another dog from the same owner ([#191](https://github.com/BOYSABIO/muttmetrics/issues/191)). Directory: dog/owner profiles + safe PATCH + **Add dog** on the owner ([#139](https://github.com/BOYSABIO/muttmetrics/issues/139), [#140](https://github.com/BOYSABIO/muttmetrics/issues/140), [#191](https://github.com/BOYSABIO/muttmetrics/issues/191)). Jinja `/capture` (stage A, #63) was removed in [#86](https://github.com/BOYSABIO/muttmetrics/issues/86) — no templates, no unauthenticated write path. Phone trial over Tailscale: [`docs/runbooks/groomer-trial.md`](./docs/runbooks/groomer-trial.md).

| Path | API calls |
|------|-----------|
| Returning dog (pick from search) | `GET /dogs?q=` → **only** `POST /visits` with known ids |
| Existing owner, new dog | `GET /owners?q=` (pick) → `POST /dogs` → visit wizard ([#191](https://github.com/BOYSABIO/muttmetrics/issues/191)) |
| Brand-new client | `POST /owners` (optional phone) → `POST /dogs` → visit; name clash without phone → **409** + candidates ([#187](https://github.com/BOYSABIO/muttmetrics/issues/187)) |
| Back-to-back second dog | After save: pick sibling or `POST /dogs`, keep `visit_date`, new timer ([#191](https://github.com/BOYSABIO/muttmetrics/issues/191)) |

**Visit wizard (#72, photos #92, money #110)** once identity is known (3 steps):

1. Optional **before photo** — `PhotoPicker` component: *Take photo* (`capture="environment"`, camera) or *Choose photo* (library), with a blob-URL preview
2. Timer — Start / Stop / Reset; elapsed → `actual_minutes` via **floor** (`Math.floor(ms / 60000)`); manual minutes always allowed
3. Details — `visit_date` defaults to **today** (local); **service** (required, from `GET /services`); **final price** (required); optional tip / quoted price; optional condition / surprise; optional **after photo** → Save → back to search

Until booking exists, the SPA sets `booked_service_id = actual_service_id`. Step-3 detail fields clear via `resetVisitDetails()` on save / cancel / new dog so leftover prices don’t stick.

UI labels are **English** (salon business language).

**Photo upload flow (#92).** The upload endpoint needs a `visit_id`, so files are held in React state and posted **after** `POST /visits` returns. Rules that are easy to break:

- **Uploads send only the key header** (`keyOnlyHeaders()` in `src/api.ts`) — a multipart body must not carry a `Content-Type` header, because the browser has to set it with the boundary marker it generates
- **Each upload has its own `try`/`catch`** — the visit is already saved, and `saveVisit`'s outer catch says "Not saved", which would be a lie
- **A `File` cannot be persisted.** The #88 draft stores `hadIntakeFile` / `hadAfterFile` booleans so the resume message can say the photo was not kept
- **`isBusy` guards both write flows.** Save and new-client Continue are disabled in flight; without it a slow phone upload invites repeat taps and duplicate rows (missed in #87, fixed in #92)
- **Leaving is guarded too (#178).** Close, Cancel visit and every Back are disabled while a save runs (Close clears the draft, so a failed save would leave nothing to retry). Close, Cancel and Reset ask first while the timer is running
- **New client keeps a half-finished owner (#178).** If the owner was created but the dog failed, a retry reuses that pending owner id (and only creates the dog). Prefer picking an existing owner from search when the name already exists (#191); a bare name-only `POST /owners` that would merge now returns **409** (#187)

**Prerequisites:** Node.js LTS (18+), repo `.env` with `API_KEY`, Postgres up, API running.

```bash
# Terminal 1 — API
python -m muttmetrics.api

# Terminal 2 — frontend
cd frontend
cp .env.example .env          # Windows: copy .env.example .env
# VITE_API_KEY must match root API_KEY
npm install
npm run dev
```

| Piece | Role |
|-------|------|
| `http://127.0.0.1:5173` | Vite **dev** server — hot reload, this PC only (`strictPort`) |
| `http://<pc-ip>:5174` | Vite **preview** server — built `dist/`, network-facing, for the groomer trial |
| `/api/*` in the SPA | Proxied to `http://127.0.0.1:8000/*` (see `frontend/vite.config.ts`) |
| `GET /dogs?q=` | Directory browse/search — returns `owner_name` on each row (cap 50) |
| `GET /owners?q=` | Owner search for capture “Already a client?” (#191) |
| `GET` / `PATCH /dogs/{id}` | Dog profile read / safe enrichment (#131, #132) |
| `GET` / `PATCH /owners/{id}` | Owner profile read / safe enrichment (#131, #132); Add dog via `POST /dogs` |
| Visit step 2 timer | Client-only; fills `actual_minutes` (floor); editable override. In-progress visit (dog + wizard + timer) persists in `localStorage` (`muttmetrics.draftVisit`) so a phone tab kill / reload can resume ([#88](https://github.com/BOYSABIO/muttmetrics/issues/88)). Cleared on save / cancel / reset. |
| `frontend/.env` | `VITE_API_KEY` (required) and `VITE_BUSINESS_NAME` (optional header name) — gitignored; never commit. Typed in `src/vite-env.d.ts` |
| `npm run build` | Production bundle to `frontend/dist/` (`tsc -b` type-checks first) |
| `npm run preview` | Serves `dist/` + the same `/api` proxy — what the groomer opens |
| `npm run e2e` | Playwright smoke against preview + a running API (#196) — see **End-to-end smoke** above |

PATCH sends only the fields you change. An explicit `null` clears an optional field (e.g. `phone`), but `null` on a required column (e.g. owner `locale`) is **422** (#177). Dog `weight_kg` must be > 0 and ≤ 150, which catches grams typed into the kg field. The Directory accepts a comma (`7,5` → 7.5) and refuses to save anything that still isn't a number, instead of sending `null` and wiping the weight (#178).

**Auth note:** `VITE_API_KEY` is baked into `frontend/dist/` at **build** time and is readable by anyone who loads the page — a gate against strangers on a private URL, never a secret. Rules and the upgrade path: [`privacy.md` → API key in the browser](./docs/architecture/privacy.md#api-key-in-the-browser). Always-on OptiPlex ([#93](https://github.com/BOYSABIO/muttmetrics/issues/93)) and cloud ([#83](https://github.com/BOYSABIO/muttmetrics/issues/83)) are iceboxed; desktop host for now.

**Phone trial (#82):** the dev server stays on `127.0.0.1`; the groomer gets `npm run build && npm run preview` on a fixed `:5174`, reachable over Tailscale only on that one port. Full procedure: [`docs/runbooks/groomer-trial.md`](./docs/runbooks/groomer-trial.md).

### Create-or-get owners & dogs (#21, #187, #191)

Onboarding helpers live in `src/muttmetrics/api/services/`. Prefer **picking** an existing owner/dog in the SPA; use POST create when this really is a new person or dog.

**JSON evening flow (maintainer / tools):**

1. `GET /owners?q=anna` → pick `owner_id`, **or** `POST /owners` with name (and phone if the name may already exist)  
2. `POST /dogs` `{"owner_id": …, "name": "Bella"}` → `dog_id` (**201** / **200**)  
3. `POST /visits` with those ids → visit row  

**`POST /owners` rules (#187):**

| Situation | Result |
|-----------|--------|
| Name is new | **201** create (phone optional) |
| Same name + phone digits match an existing row | **200** reuse |
| Same name + different phone | **201** second owner |
| Same name + no phone | **409** with `candidates` — do not silent-merge |

Phone is compared as digits only (`+49 170` ≡ `+49170`). Prefer `GET /owners?q=` in the UI so create rarely has to guess.

**Directory (returning dogs, #71):** `GET /dogs` or `GET /dogs?q=bella` → pick `dog_id` / `owner_id` → `POST /visits` (skip create). Owner profile can **Add dog** without retyping the owner name (#191).

| Endpoint | Lookup key | Notes |
|----------|------------|--------|
| `GET /owners` | optional `q` substring on name | Cap 50; LIKE wildcards escaped |
| `POST /owners` | name; phone distinguishes same-name people | See table above |
| `POST /dogs` | `(owner_id, name)` | Optional `breed_id`; **404** if owner/breed missing |

Blank names after normalize → **422**.

**Two dogs at once (#191):** log two visits (own minutes/timer each). No shared timer in v1.

### POST /visits (#20)

Creates one `visit` row after a groom. Prefer registering via `#21` endpoints above instead of raw SQL.

**Required JSON fields:** `dog_id`, `owner_id`, `visit_date`, `actual_minutes` (> 0).  
**SPA also requires for completed saves:** `actual_service_id`, `final_price` ([#110](https://github.com/BOYSABIO/muttmetrics/issues/110)).  
**Optional:** `condition_score` (0–5; **0 = worst coat … 5 = best**), `booked_service_id`, `quoted_price`, `tip`, `what_surprised_me`, `status`, `shaved_down` (when wired).

| Status | Meaning |
|--------|---------|
| 201 | Visit created — body includes `visit_id` |
| 401 | Missing/wrong API key |
| 404 | Unknown `dog_id`, `owner_id`, `booked_service_id` or `actual_service_id` |
| 422 | Validation failed (e.g. `actual_minutes: 0`, a negative price or tip, or a dog that belongs to a different owner) |

The convention across routes ([#177](https://github.com/BOYSABIO/muttmetrics/issues/177)): an id that doesn't exist is **404**; ids that exist but don't fit together, or values out of range, are **422**. Nothing a client sends should reach Postgres and come back as a 500.

Postgres must be up (`docker compose up -d`) and migrated. On Windows PowerShell, prefer `/docs` or `Invoke-RestMethod` over hand-escaped `curl -d "{\"...\"}"` (easy 422 from mangled JSON).

## Design source of truth

Product intent for day-to-day work lives in **GitHub issues/milestones**. Public framing (goals, non-goals, later ambition) is [`docs/product/vision.md`](./docs/product/vision.md). Deep local design notes may exist off-repo; if an issue and VISION disagree on boundaries, update the issue or open an ADR — do not silently invent a third model.

## Issues

GitHub issues are the task list. Do not maintain a parallel local backlog.
