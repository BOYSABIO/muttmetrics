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
5. On the capture host: `python ops/deploy.py --to vX.Y.Z`.

The groomer’s screen shows `vX.Y.Z`; `GET /health` returns the same `"version"`.

## Deploy

From the repo root, venv on, env loaded (`.env` with `API_KEY`, `DATABASE_URL`, …):

```bash
python ops/deploy.py --to vX.Y.Z --dry-run    # see the plan
python ops/deploy.py --to vX.Y.Z              # salon release (and rollback)
python ops/deploy.py --allow-main             # desktop drill from main only
```

Steps (stops on first failure):

1. Refuse a dirty tree. With `--to`: fetch tags and check the tag exists. With `--allow-main`: require the `main` branch.
2. **Backup** (`ops/backup.py`) unless `--skip-backup`, taken with the code that's still running
3. Move the code: `git checkout --detach vX.Y.Z` (or `git pull --ff-only` on main)
4. Read the version from `pyproject.toml` **now**, after the move. With `--to`, refuse if `vX.Y.Z` doesn't contain version `X.Y.Z`
5. `pip install -e .` (runtime dependencies only)
6. `alembic upgrade head`
7. `npm ci` + `npm run build` in `frontend/`
8. Restart: if `MUTTMETRICS_RESTART_CMD` is set, run it; otherwise print a manual reminder
9. Health:
   - `GET /health`: `"version"` must match step 4.
   - If `--app-url` (or `MUTTMETRICS_APP_URL`) is set: `GET <app>/api/services` must return 200. `/health` needs no key, so only a protected route proves the SPA server adds `X-API-Key` (#194).

**Why a tag is checked out, not pulled.** A checked-out tag isn't on a branch, and `git pull` needs one. The box therefore stays on the tag it last deployed, and every release or rollback is the same command: `--to` a tag.

### Desktop today

Leave `MUTTMETRICS_RESTART_CMD` unset. After deploy finishes the build:

1. Restart the API (`muttmetrics-api` / uvicorn)
2. Restart preview (`npm run preview` on `:5174`) so it serves the new `dist/` and still injects `API_KEY` (#194)

### Box later (#93)

Point the same script at systemd (example only — exact unit names live in #93):

```bash
export MUTTMETRICS_RESTART_CMD="sudo systemctl restart muttmetrics-api caddy"
export MUTTMETRICS_APP_URL="http://127.0.0.1:8080"
python ops/deploy.py --to vX.Y.Z
```

`sudo` here must not prompt (deploy runs unattended). Allow exactly that one command for the deploy user in `/etc/sudoers.d/`, nothing broader.

Caddy (or nginx) must inject `X-API-Key` on `/api/*` the same way Vite preview does (#194).

## Rollback

Decide which kind of release failed:

### A. Code only (no Alembic revision in that release)

```bash
python ops/deploy.py --to vPREVIOUS
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
