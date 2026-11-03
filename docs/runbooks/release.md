# Releases and deploy (#197)

How to ship a numbered build, put it on the capture host, and get back if something breaks.

**Not** auto-deploy on merge. CI stays the quality gate; **you** (or later the box) run `ops/deploy.py` on purpose. The OptiPlex (#93) is not required to start this ritual on the desktop.

Related: [`backup.md`](./backup.md), [`migrations.md`](./migrations.md), [`groomer-trial.md`](./groomer-trial.md), [`privacy.md`](../architecture/privacy.md) (API key on the proxy).

## What “a release” is

1. Bump version in **three** places (must stay equal — `tests/unit/test_app_versions.py`):
   - `pyproject.toml`
   - `src/muttmetrics/__init__.py` (`__version__`)
   - `frontend/package.json`
2. Move notes from `CHANGELOG.md` `[Unreleased]` into a new `## [X.Y.Z] — YYYY-MM-DD` section (no PII, no prices).
3. Merge to `main`, then tag: `git tag -a vX.Y.Z -m "vX.Y.Z"` and `git push origin vX.Y.Z`.
4. GitHub Release from that tag — paste the changelog section.
5. On the capture host: `python ops/deploy.py` (from the tag).

The groomer’s screen shows `vX.Y.Z`; `GET /health` returns the same `"version"`.

## Deploy

From the repo root, venv on, env loaded (`.env` with `API_KEY`, `DATABASE_URL`, …):

```powershell
python ops/deploy.py --dry-run --allow-main   # see the plan
python ops/deploy.py                          # from a v* tag (salon)
python ops/deploy.py --allow-main             # desktop drill from main only
```

Steps (stops on first failure):

1. Refuse dirty tree; require a `v*` tag (or `main` with `--allow-main`)
2. **Backup** (`ops/backup.py`) unless `--skip-backup`
3. `git pull --ff-only` unless `--skip-pull`
4. `pip install -e ".[dev]"`
5. `alembic upgrade head`
6. `npm ci` + `npm run build` in `frontend/`
7. Restart: if `MUTTMETRICS_RESTART_CMD` is set, run it; otherwise print a manual reminder
8. `GET /health` — `"version"` must match `pyproject.toml`

### Desktop today

Leave `MUTTMETRICS_RESTART_CMD` unset. After deploy finishes the build:

1. Restart the API (`muttmetrics-api` / uvicorn)
2. Restart preview (`npm run preview` on `:5174`) so it serves the new `dist/` and still injects `API_KEY` (#194)

### Box later (#93)

Point the same script at systemd (example only — exact unit names live in #93):

```bash
export MUTTMETRICS_RESTART_CMD="sudo systemctl restart muttmetrics-api muttmetrics-caddy"
python ops/deploy.py
```

Caddy (or nginx) must inject `X-API-Key` on `/api/*` the same way Vite preview does (#194).

## Rollback

Decide which kind of release failed:

### A. Code only (no Alembic revision in that release)

```powershell
git fetch --tags
git checkout vPREVIOUS
python ops/deploy.py --skip-pull
# or: rebuild + restart manually after checkout
```

`downgrade` is unused here — you just run the previous tag’s code on the current schema (only safe if that tag didn’t require a newer schema). Prefer rolling to a tag that matches the DB head you already have.

### B. Release included a migration

**Restore the pre-deploy backup** from step 2 of deploy. Do **not** rely on `alembic downgrade` against salon data — CI tests downgrade, but restore is the path that is always correct for real rows and photos.

1. Stop the API (and SPA server)
2. Restore DB dump per [`backup.md`](./backup.md)
3. Check out the previous tag; reinstall; rebuild SPA; start services
4. Confirm `/health` version and a Directory smoke

### Rollback drill (do once before trusting this)

Date of first desktop drill: **_YYYY-MM-DD_** (fill in when you run it).

Procedure:

1. Deploy (or dry-run then a real drill) against a **throwaway** database, not salon `muttmetrics`
2. Practice restore of the dump taken at deploy step 2 into that scratch DB
3. Note the date above

## Acceptance checklist

- [ ] SPA `v…` matches `/health.version` and the latest tag
- [ ] Release = bump + changelog + tag + `ops/deploy` (no steps from memory)
- [ ] One rollback drill done; date filled in above
