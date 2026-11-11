# Client access and erasure requests (#195)

How to answer a client who asks **what you hold** (GDPR Art. 15) or asks to be **erased** (Art. 17). Maintainer-only ops — there is no self-serve UI ([#143](https://github.com/BOYSABIO/muttmetrics/issues/143)).

Policy (anonymise, not hard-delete; backup honesty): [`privacy.md`](../architecture/privacy.md) → “Client access and erasure”.

**Where:** real data lives only on the home server ([#93](https://github.com/BOYSABIO/muttmetrics/issues/93)), so a real request runs **there**, as the app account, in the app folder. The dev PC has synthetic data only ([#222](https://github.com/BOYSABIO/muttmetrics/issues/222)); use it to rehearse (a dry run was done there on 2026-11-11), never for a real client.

```bash
ssh box@muttmetrics
sudo -iu muttmetrics
cd /opt/muttmetrics
```

The commands below assume that shell. Erasure changes data: do it **after hours**, like a deploy ([`groomer-access.md`](./groomer-access.md) §3).

## 1. Verify who is asking

Before any export or erase:

1. Confirm the person is the client (or has authority) — same channel the salon already uses for bookings is fine; do not invent a new identity system here.
2. Find the row and note **`owner_id`**. Prefer matching phone/email the salon already has on file:

   ```bash
   docker compose exec -T db psql -U muttmetrics -d muttmetrics -c "
   SELECT o.owner_id, o.name, o.phone, p.pet_id, p.name AS pet
   FROM owner o JOIN pet p USING (owner_id)
   WHERE o.name ILIKE '%<part of the name>%' ORDER BY o.owner_id;"
   ```

3. If two owners could match, stop and disambiguate — never export/erase on a guess.

## 2. Access / export (Art. 15)

```bash
.venv/bin/python ops/client_export.py --owner-id N
```

Writes a new folder under `data/exports/owner-N-<timestamp>/` (gitignored, owner-only: folder `700`, files `600`):

| File | Contents |
|------|----------|
| `owner.json` | Owner, pets, visits (incl. add-on ids), photo metadata |
| `photos/` | Copies of live JPEG files when present |
| `manifest.json` | Counts + any missing storage keys |

**Handing it over.** The folder is on the box; the client gets it through a private channel, and no copy stays behind.

1. Bundle it into `box`'s home, owner-only (as `box`: `exit` the `muttmetrics` shell first):

   ```bash
   sudo tar -C /opt/muttmetrics/data/exports -czf ~/owner-N.tgz owner-N-<timestamp>
   sudo chown box: ~/owner-N.tgz && chmod 600 ~/owner-N.tgz
   ```

2. Copy it to the PC, into a temporary folder outside any repo:

   ```powershell
   scp box@muttmetrics:owner-N.tgz $env:TEMP\
   ```

3. Send it to the client by a private channel (not GitHub, not a shared-drive link left open).
4. Delete every copy:

   ```bash
   # box
   rm ~/owner-N.tgz
   sudo -u muttmetrics rm -r /opt/muttmetrics/data/exports/owner-N-<timestamp>
   ```

   ```powershell
   # PC
   Remove-Item $env:TEMP\owner-N.tgz
   ```

**Do not commit it. Do not paste it into GitHub issues.**

## 3. Erasure (Art. 17)

Always dry-run first:

```bash
.venv/bin/python ops/client_erase.py --owner-id N            # report only, lists the photo keys
.venv/bin/python ops/client_erase.py --owner-id N --apply
```

**Keep the printed photo keys** (in the private log, §5) until #221's second copy has been cleaned: after `--apply` the rows are gone, and the keys are the only way to find that copy's files.

What `--apply` does (see privacy.md for the column list):

1. Deletes that owner’s **photos**: the live file, its copy under `<BACKUP_ROOT>/photos/`, then the row (same code as `photo_purge`)
2. Scrubs owner/pet PII to placeholders (`Erased client #N` / `Erased pet #M`)
3. Clears visit free text; **keeps** visit facts (date, minutes, prices, services)

Safe to run twice — second apply reports “Already erased”.

### After apply

- **Photo backups on the box:** already done by `--apply` (it reports how many copies it removed).
- **A second copy on another device** ([#221](https://github.com/BOYSABIO/muttmetrics/issues/221)), once it exists: remove the same keys from its `photos/` the next time it's connected.
- **Database dumps** age out on the usual schedule (14 days daily, 8 weeks for retained Sundays). Do not rewrite old dumps.

## 4. What to tell the client

Honest, short:

- Their contact details, notes, and photos are removed from the live system.
- Anonymous visit history (dates, durations, prices) may remain for the salon’s records and product improvement; it is not linked to their name or contact details.
- Older backups can still hold a copy until they expire (about two weeks for daily dumps, up to eight weeks for retained Sundays).

Do not promise “gone from every copy instantly.”

## 5. Private log

Note privately (not in git) that the request happened: date, `owner_id`, export and/or erase, who verified identity, and the photo keys from §3 until #221's copy is cleaned. Salon paper notebook or an offline note is enough for v1.

## Related

- [`photos.md`](./photos.md) §5 — photo-only purge
- [`backup.md`](./backup.md) §6 — the backup side of deletions
- [`ops/README.md`](../../ops/README.md) — script index
- [`privacy.md`](../architecture/privacy.md) — anonymise decision and backup table
