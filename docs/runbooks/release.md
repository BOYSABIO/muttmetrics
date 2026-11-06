# Releases and deploy (#197)

How to ship a numbered build, put it on the home server ([#93](https://github.com/BOYSABIO/muttmetrics/issues/93)), and get back if something breaks.

**Not** auto-deploy on merge. CI is the quality gate; **you** run `ops/deploy.py` on purpose. Merging changes nothing on the box: only a tag you deploy does.

## From a branch to the groomer's phone

| Step | Where | What |
|---|---|---|
| 1. Branch, build, try | dev PC | Feature branch; the dev database holds **synthetic data only** ([#222](https://github.com/BOYSABIO/muttmetrics/issues/222)) |
| 2. Test | dev PC | `pytest` (on `muttmetrics_test`, guarded), `ruff`, `npm run lint` / `build` |
| 3. PR → merge | GitHub | CI: tests, migration round-trip, end-to-end smoke, audits. Several PRs can be merged before a release |
| 4. Release | dev PC | Bump + changelog + tag + GitHub release (below) |
| 5. Deploy | home server | `ops/deploy.py --to vX.Y.Z` (below), after hours |
| 6. Check | phone | The footer shows `vX.Y.Z` |

Related: [`backup.md`](./backup.md), [`migrations.md`](./migrations.md), [`home-server.md`](./home-server.md) (the host), [`privacy.md`](../architecture/privacy.md) (API key on the proxy).

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

On the home server, as the app account, from the checkout:

```bash
ssh <admin>@muttmetrics
sudo -iu muttmetrics                          # MUTTMETRICS_RESTART_CMD / _APP_URL come from its ~/.profile
cd /opt/muttmetrics
.venv/bin/python ops/deploy.py --to vX.Y.Z --dry-run    # see the plan
.venv/bin/python ops/deploy.py --to vX.Y.Z              # release (and rollback)
```

`--allow-main` deploys the tip of `main` instead of a tag: for a throwaway drill only, never on the box. Deploy **after hours**: the restart takes seconds, and a save in that moment becomes a draft the groomer has to retry.

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
   - `GET /health`: `"version"` must match step 4. It retries for up to `--health-timeout` seconds (default 30), because `systemctl restart` returns before the API is listening.
   - If `--app-url` (or `MUTTMETRICS_APP_URL`) is set: `GET <app>/api/services` must return 200. `/health` needs no key, so only a protected route proves the SPA server adds `X-API-Key` (#194).

**Why a tag is checked out, not pulled.** A checked-out tag isn't on a branch, and `git pull` needs one. The box therefore stays on the tag it last deployed, and every release or rollback is the same command: `--to` a tag.

**A release that changes `deploy.py` itself runs the *old* script once.** Python has already loaded the old version when step 3 checks out the new code, so that one deploy uses the old logic. If it stumbles on something the new version fixes (as the 0.6.2 → 0.6.3 deploy did: "Connection refused" at step 9), **re-run `--to` the same tag**. It's safe: another backup, the same checkout, the same build.

**Box wiring** (files in [`ops/server/`](../../ops/server/README.md)):

- **Step 8** runs `MUTTMETRICS_RESTART_CMD="sudo systemctl restart muttmetrics-api caddy"`. The sudoers file lets `muttmetrics` run exactly that, without a password, and nothing else.
- **Step 9** checks the proxy at `MUTTMETRICS_APP_URL=http://127.0.0.1:8080` (Caddy), which injects `X-API-Key` the way Vite does in dev (#194).

Never edit, `npm audit fix` or upgrade npm inside `/opt/muttmetrics`: the box builds exactly what a tag says, and step 1 refuses a dirty tree.

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

### Rollback drill

Done on the home server on **2026-11-06**: `--to v0.6.2` (code-only rollback, `Deploy OK.`), then `--to v0.6.3` forward again. That forward run stumbled once at step 9 on the old script and passed on the re-run, exactly as described above. Restoring a dump (type B) is drilled through [`backup.md`](./backup.md) §5 (also 2026-11-06).

Re-drill after a change to `deploy.py`, and before a release whose migration touches existing data.

## Acceptance checklist

- [ ] SPA `v…` matches `/health.version` and the latest tag
- [ ] Release = bump + changelog + tag + `ops/deploy` (no steps from memory)
- [x] One rollback drill done (2026-11-06)
