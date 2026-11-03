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

[Unreleased]: https://github.com/BOYSABIO/muttmetrics/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/BOYSABIO/muttmetrics/releases/tag/v0.6.0
