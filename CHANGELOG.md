# Changelog

All notable changes to MuttMetrics are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
starting at **0.6.0** for M6 (production-ready track).

Do **not** put client names, phone numbers, prices, or salon counts in this file.

## [Unreleased]

### Added

- Monitoring for the home server ([#104](https://github.com/BOYSABIO/muttmetrics/issues/104)): a heartbeat every 5 minutes (through Caddy to a route that needs the database, so one ping proves the whole chain; `/fail` if it breaks) and a success/failure report after every nightly backup, both to Healthchecks.io. The box only makes outgoing requests and sends no client data. Reference units in `ops/server/systemd/`, the env template in `ops/server/monitoring/`, setup in `home-server.md` §A5b
- `ops/server/apt/20auto-upgrades` and `ops/server/tailscale/policy-snippet.hujson` (the tag, the groomer's 443 grant and its test, with a placeholder group), so the whole box can be rebuilt from `ops/server/`

### Changed

- The backup unit's Healthchecks report is optional (`EnvironmentFile=-…`; no URL = no report), so a rebuild works in any order and the backup never depends on monitoring

### Fixed

## [0.6.4] — 2026-11-08

One database migration (deploy backs up first). Nothing changes on the groomer's screen.

### Added

- `visit.created_at`: when a visit was saved, set by Postgres, so visits backfilled later (dated in the past) can be told apart from ones logged on the day. Existing visits stay `NULL` (unknown) on purpose: the migration adds the column first and only then the `DEFAULT now()`, so it can't stamp old rows with the migration time. Not used by the compliance SQL yet ([#224](https://github.com/BOYSABIO/muttmetrics/issues/224)); included in the GDPR export
- `ops/server/`: reference copies of the home server's config (systemd units, Caddyfile, nftables, SSH hardening, Docker `daemon.json`, sudoers, unattended-upgrades reboot), with placeholders instead of addresses and names. `tests/unit/test_server_files.py` keeps the folder free of private addresses, tailnet names and secrets, and pins the lines the security model relies on
- Runbooks: `home-server.md` (rebuild from scratch with a check per step, day-to-day jobs, troubleshooting) and `groomer-access.md` (the groomer's phone), replacing the desktop-era `groomer-trial.md`

### Changed

- `npm run preview` binds to `127.0.0.1`: it no longer serves the groomer, and the dev PC shouldn't listen on the network
- Docs describe the home server as the host: `release.md` (branch → phone flow, box deploy, the rollback drill done 2026-11-06, the "old deploy script runs once" caveat), `backup.md` (systemd timer, box paths, stdin restore), `privacy.md` (where the data lives), README status, CONTRIBUTING

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

[Unreleased]: https://github.com/BOYSABIO/muttmetrics/compare/v0.6.4...HEAD
[0.6.4]: https://github.com/BOYSABIO/muttmetrics/releases/tag/v0.6.4
[0.6.3]: https://github.com/BOYSABIO/muttmetrics/releases/tag/v0.6.3
[0.6.2]: https://github.com/BOYSABIO/muttmetrics/releases/tag/v0.6.2
[0.6.1]: https://github.com/BOYSABIO/muttmetrics/releases/tag/v0.6.1
[0.6.0]: https://github.com/BOYSABIO/muttmetrics/releases/tag/v0.6.0
