# Client access and erasure requests (#195)

How to answer a client who asks **what you hold** (GDPR Art. 15) or asks to be **erased** (Art. 17). Maintainer-only ops — there is no self-serve UI ([#143](https://github.com/BOYSABIO/muttmetrics/issues/143)).

Policy (anonymise, not hard-delete; backup honesty): [`privacy.md`](../architecture/privacy.md) → “Client access and erasure”.

## 1. Verify who is asking

Before any export or erase:

1. Confirm the person is the client (or has authority) — same channel the salon already uses for bookings is fine; do not invent a new identity system here.
2. Find the row in Directory (or SQL) and note **`owner_id`**. Prefer matching phone/email the salon already has on file.
3. If two owners could match, stop and disambiguate — never export/erase on a guess.

## 2. Access / export (Art. 15)

```powershell
# venv on, repo root, API/DB env loaded as usual
python ops/client_export.py --owner-id N
```

Writes a new folder under gitignored `data/exports/owner-N-<timestamp>/`:

| File | Contents |
|------|----------|
| `owner.json` | Owner, pets, visits (incl. add-on ids), photo metadata |
| `photos/` | Copies of live JPEG files when present |
| `manifest.json` | Counts + any missing storage keys |

Hand the folder to the client by a private channel. **Do not commit it. Do not paste it into GitHub issues.**

## 3. Erasure (Art. 17)

Always dry-run first:

```powershell
python ops/client_erase.py --owner-id N
python ops/client_erase.py --owner-id N --apply
```

What `--apply` does (see privacy.md for the column list):

1. Deletes that owner’s **photos** (files then rows) via the same path as `photo_purge`
2. Scrubs owner/pet PII to placeholders (`Erased client #N` / `Erased pet #M`)
3. Clears visit free text; **keeps** visit facts (date, minutes, prices, services)

Safe to run twice — second apply reports “Already erased”.

### After apply (photos in backups)

Live photo files under `PHOTO_ROOT` are gone. Additive copies under `BACKUP_ROOT/photos/` must still be removed by hand when you follow [`backup.md`](./backup.md) §6 (same step as after a plain `photo_purge`). Database dumps age out on the usual schedule — do not rewrite old dumps.

## 4. What to tell the client

Honest, short:

- Their contact details, notes, and photos are removed from the live system.
- Anonymous visit history (dates, durations, prices) may remain for the salon’s records and product improvement; it is not linked to their name or contact details.
- Older backups can still hold a copy until they expire (about two weeks for daily dumps, up to eight weeks for retained Sundays).

Do not promise “gone from every copy instantly.”

## 5. Private log

Note privately (not in git) that the request happened: date, `owner_id`, export and/or erase, who verified identity. Salon paper notebook or an offline note is enough for v1.

## Related

- [`photos.md`](./photos.md) §5 — photo-only purge
- [`ops/README.md`](../../ops/README.md) — script index
- [`privacy.md`](../architecture/privacy.md) — anonymise decision and backup table
