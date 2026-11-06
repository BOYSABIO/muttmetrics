# Changelog

All notable changes to MuttMetrics are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
starting at **0.6.0** for M6 (production-ready track).

Do **not** put client names, phone numbers, prices, or salon counts in this file.

## [Unreleased]

### Added

### Changed

### Fixed

## [0.6.3] — 2026-11-06

Found during the first deploy on the home server (#93). Nothing changes on the groomer's screen.

### Fixed

- `ops/deploy.py` checked `/health` the instant `systemctl restart` returned, before the API was listening, so a good deploy failed with "Connection refused". It now waits up to `--health-timeout` (30 s) for the new version to answer, and the proxy check waits the same way instead of crashing when nothing answers
- `ops/backup.py` wrote dumps and photo copies readable by other local users when run from a login shell; they're now owner-only (umask 077)

## [0.6.2] — 2026-11-05

Groundwork for the home server (#93). Nothing changes on the groomer's screen.

### Changed

- `ops/deploy.py --to vX.Y.Z` deploys (or rolls back to) a release tag: backup, then checkout, then read the version. It installs runtime dependencies only, and with `--app-url` it checks that the SPA server's `/api` proxy adds the key
- The Postgres password comes from `POSTGRES_PASSWORD` in `.env` instead of being written in `docker-compose.yml`
- The backup timer example runs as an unprivileged `muttmetrics` user

### Fixed

- Deploying from a tag failed at `git pull`, because a checked-out tag isn't on a branch. Deploying from `main` reported a false version mismatch when the pull bumped the version
- The restore-drill and db-peek count queries still used the `dog` table, which 0.6.0 renamed to `pet`

## [0.6.1] — 2026-11-03

### Changed

- Dev tooling: `actions/setup-python` v7, ruff 0.17.3 (pyproject + pre-commit lockstep), typescript-eslint 8.72.1 (TypeScript stays on ~6.0.2 for peer range)

## [0.6.0] — 2026-11-03

First numbered M6 release. Earlier work shipped without semver tags; this is the
baseline the groomer's screen and `/health` can name.

### Added

- Version shown in the app and on `GET /health` (and Alembic revision when the DB is up)
- Client data export and anonymising erase for GDPR requests
- API key stays on the Vite proxy — not in the browser bundle
- Cats as first-class clients (species on pets, breeds, size bands)
- Technique / add-on catalog on visits
- Release / deploy / rollback runbook and `ops/deploy.py`

### Changed

- Metrics period fields use neutral `start` / `end` names
- Dog table and `/dogs` API renamed to `pet` / `/pets`

### Fixed

- Insecure / short `API_KEY` values refused at API (and proxy) startup

[Unreleased]: https://github.com/BOYSABIO/muttmetrics/compare/v0.6.3...HEAD
[0.6.3]: https://github.com/BOYSABIO/muttmetrics/releases/tag/v0.6.3
[0.6.2]: https://github.com/BOYSABIO/muttmetrics/releases/tag/v0.6.2
[0.6.1]: https://github.com/BOYSABIO/muttmetrics/releases/tag/v0.6.1
[0.6.0]: https://github.com/BOYSABIO/muttmetrics/releases/tag/v0.6.0
