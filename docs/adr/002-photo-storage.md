# Architecture Decision Record

## ADR-002: Photo bytes on disk, metadata in Postgres

- **Status:** Accepted
- **Date:** 2026-09-27
- **Context:** Capture needs real photo upload from a phone ([#30](https://github.com/BOYSABIO/muttmetrics/issues/30), [#92](https://github.com/BOYSABIO/muttmetrics/issues/92)). The URL-paste stub from the visit wizard was a developer placeholder — the groomer's photos live on a phone camera roll, not behind a link. Storing them introduces the first binary data in the project, and the first personal data with real size.

### Decision

**Bytes on the filesystem under a configured root outside the repo; one `photo` row per file in Postgres.**

1. **Not `bytea`.** Postgres can store the bytes, and doing so would give real transactions, one backup artifact and no orphan files. It was rejected because the backup ([#95](https://github.com/BOYSABIO/muttmetrics/issues/95)) is a daily `pg_dump`: photos in the database turn that into a multi-GB full dump every night, while on disk they are an incremental file copy. Secondary costs: whole values held in memory per request, no streaming, slow restores.
2. **Root outside the repo** (`PHOTO_ROOT`, default `~/muttmetrics-data/photos`). Client photos must not be one `git add -f` away from a public repository. Same category as the `muttmetrics_pgdata` Docker volume: data the project manages, not source.
3. **A `photo` table, not the `visit.intake_photos` / `after_photos` arrays.** Arrays cannot carry per-photo metadata, have no `created_at` for retention, cannot express a dog profile photo that belongs to no visit, and make "every file belonging to this client" an unnest across two columns. The arrays are **deprecated, not dropped** — see [#98](https://github.com/BOYSABIO/muttmetrics/issues/98) for the contract step.
4. **The database stores a relative key**, never an absolute path or a URL. Moving the host ([#93](https://github.com/BOYSABIO/muttmetrics/issues/93)) is then copy the directory and change one env var — not an `UPDATE` across live rows.
5. **Foreign keys without `ON DELETE CASCADE`.** Postgres cannot delete files. A cascade would drop rows and strand bytes on disk forever; refusing the delete forces the documented procedure that removes files first.

### Consequences

- **Two systems with no shared transaction.** Everything else follows from this: write the file first (an orphan file is invisible litter a sweeper removes), insert the row last (a row without its file is a broken promise), write to a temp name and rename atomically, and reconcile disk against database periodically.
- **Everything stored is a re-encoded JPEG with no metadata.** Uploads are decoded (which is the real validation), EXIF-rotated, stripped, downscaled and re-encoded. GPS coordinates from a phone never reach the disk.
- **Serving requires the API.** Photos are behind `X-API-Key`, so a browser `<img src>` cannot fetch one directly — the SPA fetches bytes and renders a blob URL (#92).
- **Deletion is application code, not SQL.** Rows, files and backup copies are three separate things; `docs/privacy.md` states what happens to each.

### Alternatives considered

- **`bytea` in Postgres** — rejected above; revisit only if backup strategy changes fundamentally.
- **Object storage (R2 / S3) now** — real answer for a hosted deployment ([#83](https://github.com/BOYSABIO/muttmetrics/issues/83)), premature while capture runs on one desktop. The `storage_backend` column exists so this can be added per-row rather than as a migration.
- **Keep pasting URLs** — rejected: no groomer will ever do it.
