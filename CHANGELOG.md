# Changelog

All notable changes to MuttMetrics are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
starting at **0.6.0** for M6 (production-ready track).

Do **not** put client names, phone numbers, prices, or salon counts in this file.

## [Unreleased]

## [0.7.0] — 2026-11-14

First M6.5 release: capture and the pet profile cleaned up, so they're quicker to use and the data is clean enough to train a model on later. **Three migrations; `c9d0e1f2a3b4` rewrites existing pet rows** (coat, size, sex): run the read-only checks in the release notes first. **On the box, after deploying:** `python -m muttmetrics.seed --breeds-only` (never the plain seed there).

### Added

- **About 60 more breeds, and "Add a breed".** The catalog grows from 20 to 77: common salon breeds and the doodle crosses, each with starting-guess typical minutes, matting risk, coat and size for the estimate (`seed/data.py`; the groomer corrects them). Breeds show their English name; typing the German one still finds them, accents optional ("schafer" → German Shepherd). When nothing matches, the picker offers *Add "X" as a breed* (`POST /breeds`): it's marked as added in the salon, and a twin with other capitals or the German name gets the existing breed back instead. A breed added in the salon has no typical minutes, so its dogs get no estimate until someone sets them. `python -m muttmetrics.seed --breeds-only` updates just the breeds (the full seed also rewrites services and would blank prices without the private pricing file)
- **Time vs estimate tells you what it means.** The timing card now says whether estimates run short, are cautious or are about right (a worst case should be beaten about 1 in 10 times), and shows every groom with an estimate as one bar: within the typical time / longer but within the worst case / past it. New SQL function `metric_estimate_bands` (migration `b8c9d0e1f2a3`, `analytics.md` "Estimate bands")
- `python ops/demo_data.py --recent`: about 12 weeks of synthetic visits ending today (`ops/demo_recent.py`), so the dev dashboard and video footage show current weeks: repeat dogs with history and estimates, owners with two dogs groomed back to back, cats, add-ons, tips, bad coats undercharged, and dog profiles only partly filled. Invented names and prices, fixed random seed, still only into an empty database; CI's e2e data is unchanged

### Changed

- **The pet profile, redone.** The top says what matters at a glance: breed · size · coat · handling, visits and how long ago, and heads-up tags (*Muzzle*, *Two people*, *Senior*, *Health note*). Then **Basics**, the four facts the estimate leans on, as taps with a "3 of 4" count: breed, size (S/M/L/XL by eye, or from the weight), coat (with a one-line hint per type), handling (*Easy … Very difficult*). Then grooming notes (usual cut, thickness, temperament, health), recent visits, and a folded *More details* (name, species, crossed with, weight, sex, and Yes / No for muzzle, two people, senior, where neither means nobody checked). On a computer: facts left, visits and details right. The bar says *Unsaved changes*, and Back asks before throwing them away
- **Pet profile data cleaned up so it can feed a model later** (migration `c9d0e1f2a3b4`, new `docs/architecture/pet-data.md`, ADR-001 amended). Every field a model may use is now a fixed list the database enforces (`src/muttmetrics/pet_vocab.py`):
  - **Coat:** one coat type per species: dog *Smooth, Double, Curly, Wire, Long & silky, Combination*; cat *Short-haired, Long-haired*. "Single" became "Long & silky", and *Wire* is new. Plus *Thickness* (thin / normal / thick, from the old density). Hair/fur, undercoat and sheds followed from the type and left the profile (the columns stay until a later cleanup)
  - **Size can be picked by eye** when the dog wasn't weighed; a weight still wins. A new `size_source` says which (`weight` / `eye`). Breed hints use the same four sizes (no more "xs")
  - **Blank stays blank:** saving the profile only sends what changed. Before, any save wrote "no" into every unticked box (muzzle, two-person, senior…), so "nobody checked" and "no" looked the same. Sex is *Female / Male* or blank (no "unknown" value)
  - **New:** *Usual cut* (the cut the dog usually gets), and one *Health notes* box (mobility and vet notes merged into it). Handling shows words (*Easy … Very difficult*); the stored 1–5 is unchanged
  - **Change log:** each profile save that changes a structured fact (size, coat, handling, breed…) writes a `pet_change` row, so an analysis can use what was known on a visit's date. No names or notes in it. Client export includes it; erase also wipes the new notes
  - Breeds: English names are unique per species (any capitalisation), and a breed records whether it came with the app or was added in the salon. The seed matches breeds by species + name
- **Coat condition is a word, not a number.** Capture and visit edits ask it as six taps (*Matted, Rough, Tangled, OK, Good, Great* for 0–5; tap again to clear) instead of a 0–5 field, and the dashboard uses the same words. "Coat 1" was easy to mix up with the dog's coat *type*. The stored value is still 0–5; the words live in one place (`frontend/src/condition.ts`) so they can change after the groomer has tried them
- **New visit works on a computer.** It was a phone strip in the middle of the screen; now the pets to pick from fill the width (2–3 per row) and the visit form uses two fields per row, while forms stay a readable column. The phone layout is unchanged
- **Buttons are in the same place on every screen** (`docs/architecture/ui-conventions.md`), so a thumb that learned one screen can't hit Delete or Save on the next. Leaving is always top left (*← Back* on pages, *✕ Close* in New visit; the bottom *Cancel visit* is gone). The bottom bar always ends with the main action on the right (*Save changes*, *Continue*, *Save visit*) with *← Back* to its left. *Delete visit* moved out of the bar into its own box at the end of the visit page, on the left, away from Save. *Start visit* moved up next to the dog's name. The header has *Home* and *Clients* tabs (Home used to be only the logo). In the inline Add pet form, *Cancel* is now left of *Add pet*
- **New visit: the bottom buttons stay put, and the timer step was redesigned.** The three steps share one bar pinned to the bottom of the screen (on a computer, the bottom of the card, which now scrolls inside), so *Continue* is in the same spot on every step instead of following the content. A step tracker (*Photo · Time · Details*) replaces "Step 2 of 3". The timer step is one big clock with a single *Start timer* / *Stop timer* button and a small *Reset timer*; "Minutes groomed" fills in when you stop and can be typed instead. Step 3's fields on a phone got even spacing
- **€ / hour by coat: every shave-down is one row** (migration `a7b8c9d0e1f2`, `analytics.md` amended). It was condition × shaved, up to 12 rows; shave-downs happen almost only on bad coats, so most "· shaved" rows could never fill. Now 6 conditions + "Shave-down" = 7 rows, and the coat sentence reads "Good coats earn €X an hour more than shave-downs"

## [0.6.7] — 2026-11-11

Owner-only files everywhere, and an erase that reaches the photo backups. No migration. **On the box, once:** reinstall `muttmetrics-api.service` (it gains `UMask=0077`) — see the release notes.

### Security

- **Photos are owner-only (`600`), and so are their backup copies.** The API service had no `UMask`, so new photos were written `644`, and `ops/backup.py` copied that mode into the backups (`shutil.copy2` copies permission bits; the umask from 0.6.3 didn't apply). The folders were all `700`, so nothing was readable by another account; the files now match. `UMask=0077` in `ops/server/systemd/muttmetrics-api.service` (pinned by `test_server_files.py`), and `backup.py` sets `600` on every copy
- **Client exports are owner-only** (folder `700`, files `600`) instead of following the caller's umask

### Changed

- The dev PC no longer holds real client data ([#222](https://github.com/BOYSABIO/muttmetrics/issues/222)): its database was recreated from synthetic fixtures, and dev photos/backups go to the repo's gitignored `data/dev/`. `privacy.md`, CONTRIBUTING, `photos.md` and `db-peek.md` say so. The pre-move data folder stays frozen as the second copy until [#221](https://github.com/BOYSABIO/muttmetrics/issues/221)

### Fixed

- **Erasing a client now removes their photo backup copies too** (found in the export/erase dry run, #198). `client_erase.py --apply` and `photo_purge.py --apply` delete each photo's copy under `<BACKUP_ROOT>/photos/` with the live file, report how many, and print the keys, which are the only record left for cleaning another copy (#221). Before, the runbook said to remove them by hand, but `client_erase` never showed the keys, and after `--apply` they were gone
- `client-requests.md` describes a real request on the home server: where to run it, how the export reaches the client without staying on the dev PC, and what to log
- Lifetime numbers were shown twice: week and month still had the "Since day one" card next to the new **All** mode. That card is gone; week and month end with a one-line link instead (grooms so far, how many to the next milestone, and "All time →", with the milestone as a thin bar) that switches to All
- All mode's date capsule was cut off ("Sep 22 – Nov…") and kept the dividers of the missing arrows. It now reads "Since Sep 22" and has the same width as in week and month, so the control doesn't jump when switching
- The All time hero repeated "since …" under the total; it now shows the tips split like the other modes (the capsule says since when)
- On a wide screen, Last 90 days alone took half the row and left the other half empty; a card on its own now spans the row (its coat rows keep a readable width)

## [0.6.6] — 2026-11-10

This week screen polish and tooling bumps. No migration.

### Added

- **All time** on the period toggle (Week · Month · All): lifetime take-home, grooms, hours and € / hour in the hero, with the next groom milestone. The date capsule shows first groom → today; the separate "Since day one" card is folded into this mode so it isn't shown twice

### Changed

- Bottom cards on This week stretch to equal height and equal width so Last 90 days and Since day one line up
- Dev tooling: ruff 0.17.4 (pyproject + pre-commit lockstep), Playwright 1.65.0, Vite 8.3.6

## [0.6.5] — 2026-11-08

A new This week screen ([#228](https://github.com/BOYSABIO/muttmetrics/issues/228)). No migration: the API passes new date ranges to the same SQL functions.

### Added

- **This week, rebuilt around what the groomer checks:** take-home as the big number, with grooms, hours and € / hour under it, each with ↑ / ↓ against last week (or last month). While a period is still running it's compared with the same days of the previous one ("at this point"), so a Tuesday isn't measured against a whole week
- **Day by day:** Mon–Sun bars of actual hours against the day cap, today highlighted, days over the cap marked (week by week in month view)
- **Last 90 days:** € / hour by coat now uses the last 90 days, whatever week or month is selected: up to 12 coat rows can't fill inside one week. One sentence compares the coats; rows still under 5 grooms show as "filling up" chips with their count
- **Since day one:** all-time grooms, hours and take-home, with the next milestone (25 → 50 → 100 …)
- API `/metrics/period` returns `recent` (`RECENT_DAYS` = 90), `all_time` and `previous_is_partial`; the definitions are in `analytics.md`
- Monitoring for the home server ([#104](https://github.com/BOYSABIO/muttmetrics/issues/104)): a heartbeat every 5 minutes (through Caddy to a route that needs the database, so one ping proves the whole chain; `/fail` if it breaks) and a success/failure report after every nightly backup, both to Healthchecks.io. The box only makes outgoing requests and sends no client data. Reference units in `ops/server/systemd/`, the env template in `ops/server/monitoring/`, setup in `home-server.md` §A5b
- `ops/server/apt/20auto-upgrades` and `ops/server/tailscale/policy-snippet.hujson` (the tag, the groomer's 443 grant and its test, with a placeholder group), so the whole box can be rebuilt from `ops/server/`

### Changed

- The backup unit's Healthchecks report is optional (`EnvironmentFile=-…`; no URL = no report), so a rebuild works in any order and the backup never depends on monitoring
- The timing numbers ("ran long", "past worst case") appear only once visits carry a time estimate, and then over 90 days. None do yet: new clients created at capture have no breed, and the estimate comes from the breed ([#121](https://github.com/BOYSABIO/muttmetrics/issues/121))
- Docs: the second backup copy ([#221](https://github.com/BOYSABIO/muttmetrics/issues/221)) is no longer an M6 gate; until it exists, losing the box's disk is an accepted risk, written down in `privacy.md` and `backup.md`

### Removed

- The "Plan changes" row ([#188](https://github.com/BOYSABIO/muttmetrics/issues/188) was decided not planned, so it could only ever say "not captured"), and the Day load list with its planned bars (it judged a day on estimates that don't exist yet)

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

[Unreleased]: https://github.com/BOYSABIO/muttmetrics/compare/v0.7.0...HEAD
[0.7.0]: https://github.com/BOYSABIO/muttmetrics/releases/tag/v0.7.0
[0.6.7]: https://github.com/BOYSABIO/muttmetrics/releases/tag/v0.6.7
[0.6.6]: https://github.com/BOYSABIO/muttmetrics/releases/tag/v0.6.6
[0.6.5]: https://github.com/BOYSABIO/muttmetrics/releases/tag/v0.6.5
[0.6.4]: https://github.com/BOYSABIO/muttmetrics/releases/tag/v0.6.4
[0.6.3]: https://github.com/BOYSABIO/muttmetrics/releases/tag/v0.6.3
[0.6.2]: https://github.com/BOYSABIO/muttmetrics/releases/tag/v0.6.2
[0.6.1]: https://github.com/BOYSABIO/muttmetrics/releases/tag/v0.6.1
[0.6.0]: https://github.com/BOYSABIO/muttmetrics/releases/tag/v0.6.0
