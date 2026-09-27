# Ops: capture photos — where they live, how to move them, how to delete them

Operational reference for photo storage ([#30](https://github.com/BOYSABIO/muttmetrics/issues/30)). Design rationale is in [ADR-002](./adr/002-photo-storage.md); the privacy policy this implements is in [`privacy.md`](./privacy.md).

Related: [`ops-db-peek.md`](./ops-db-peek.md) (looking at rows), [`ops-enrichment.md`](./ops-enrichment.md) (fixing rows), [`ops-handoff-trial.md`](./ops-handoff-trial.md) (running the stack).

---

## 0. The short version

| Thing | Where |
|-------|-------|
| Photo **bytes** | on disk under `PHOTO_ROOT`, **outside the repo** |
| Photo **metadata** | `photo` table in Postgres |
| What the DB stores | a **relative** key: `YYYY/MM/<uuid4hex>.jpg` |
| What is stored | re-encoded JPEG, EXIF stripped, long edge ≤ 1600px |
| Who can read them | anything with the API key, via `GET /photos/{photo_id}` |

Files and rows are two systems with no shared transaction. Everything below follows from that.

## 1. Configuration

```env
# .env — outside the repo on purpose
PHOTO_ROOT=C:/muttmetrics-data/photos
```

Unset, it defaults to `~/muttmetrics-data/photos`. The directory is created on first write; nothing needs to exist beforehand.

Layout on disk:

```text
<PHOTO_ROOT>/
  2026/
    09/
      3f6a1c9e8b4d47f2a0d5e7c1b9a2f403.jpg
      7b21e0d5a9c14f6e8d3b5a7c9e1f2043.jpg
```

Month comes from **upload time**, not visit date — it is the only input always available (a profile photo has no visit; a late upload has a past visit date). Nothing about the dog, owner or visit appears in the path: a filename is data too.

## 2. API

| Route | Auth | Purpose |
|-------|------|---------|
| `POST /visits/{visit_id}/photos` | `X-API-Key` | multipart upload (`file`, optional `kind=intake\|after`) |
| `GET /visits/{visit_id}/photos` | `X-API-Key` | metadata list, oldest first |
| `GET /photos/{photo_id}` | `X-API-Key` | the JPEG bytes |

Status codes: **413** upload too large (15MB), **415** not a decodable image, **404** unknown visit or photo, **401** missing or wrong key.

Smoke test with the API running:

```bash
curl.exe -s -X POST "http://127.0.0.1:8000/visits/1/photos" ^
  -H "X-API-Key: %API_KEY%" ^
  -F "file=@C:/path/to/photo.jpg" ^
  -F "kind=intake"
```

**`<img src>` cannot load these** — a plain image tag sends no headers, so it cannot present the API key. The SPA fetches the bytes and renders a blob URL ([#92](https://github.com/BOYSABIO/muttmetrics/issues/92)).

## 3. What happens to an upload

1. Reject on size before decoding.
2. **Decode** — this is the real validation; the filename and declared content type are only claims.
3. **Apply EXIF rotation**, then drop all metadata (GPS, timestamps, device model) by re-encoding without it.
4. Downscale to ≤ 1600px on the long edge, re-encode JPEG (quality 85).
5. Write to a temp file in the same directory, `fsync`, **atomic rename**.
6. Insert the `photo` row.

Order matters: a file with no row is invisible litter a sweeper removes; a row with no file is a promise that cannot be kept. If the insert fails, the file is deleted immediately as a best effort, and the sweeper is the backstop.

## 4. Looking at what is there

```sql
-- photos for one visit
SELECT photo_id, kind, content_type, byte_size, created_at, storage_key
FROM photo
WHERE visit_id = :visit_id
ORDER BY photo_id;

-- everything for one client (this is the query deletion depends on)
SELECT p.photo_id, p.storage_key, d.name AS dog, o.name AS owner
FROM photo p
JOIN dog d ON d.dog_id = p.dog_id
JOIN owner o ON o.owner_id = d.owner_id
WHERE o.owner_id = :owner_id;

-- how much disk the rows think they use
SELECT count(*) AS photos, pg_size_pretty(sum(byte_size)) AS total
FROM photo;
```

## 5. Deleting a client's photos

Three separate things hold photo data, and a deletion request has to address all three honestly.

```bash
# 1. See what would go (default: dry run, changes nothing)
python scripts/photo_purge.py --owner-id 42

# 2. Do it
python scripts/photo_purge.py --owner-id 42 --apply
```

The script deletes **files first, then rows** — the reverse of the write order, for the same reason: never leave a row pointing at bytes that are gone.

3. **Backups still contain the photos** until the retention window in [`privacy.md`](./privacy.md) passes. Tell the client that; do not claim an instant total erase.

A browser that displayed a photo may also keep it in its cache for up to an hour (`Cache-Control: private, max-age=3600`).

## 6. Orphan sweep

Files with no row. Normal causes: a crash between write and insert, or a `.tmp` left by an interrupted write.

```bash
python scripts/photo_sweep.py            # report only
python scripts/photo_sweep.py --apply    # delete them
```

Only files older than one hour are considered, so an upload in flight is never swept. Worth running occasionally, and after any crash during a capture session.

## 7. Backups

Photos are covered by [#95](https://github.com/BOYSABIO/muttmetrics/issues/95) as an **incremental file copy** of `PHOTO_ROOT`, separate from the database dump. Rough sizing: ~1 GB/year at three grooms a day after downscaling.

## 8. Moving to another host (#93)

1. Stop the API.
2. Copy `PHOTO_ROOT` to the new machine (`robocopy` / `rsync -a`).
3. Set `PHOTO_ROOT` in the new `.env`.
4. Restore the database.

No rows change: the key is relative, which is the whole reason it is stored that way.

## 9. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| 415 on a photo that opens fine on the phone | HEIC without `pillow-heif` installed | `pip install -e ".[dev]"` |
| 413 | over 15MB | downscale on the client (#92), or raise `MAX_UPLOAD_BYTES` deliberately |
| `GET /photos/{id}` returns 404 "file is missing" | row survived, file did not (manual delete, failed restore, wrong `PHOTO_ROOT`) | check `PHOTO_ROOT`; if genuinely gone, delete the row |
| Photos appear rotated | EXIF orientation was not applied — should be impossible via the API | check the upload went through `POST /visits/{id}/photos`, not a manual file copy |
| Disk filling up | uploads are not downscaled or the sweeper never runs | check `MAX_EDGE`, run the sweep |
