# Privacy

MuttMetrics handles real client-adjacent business data for a dog grooming shop in the EU, so GDPR applies. This document is not legal advice; it is the engineering checklist for what data we store, what never belongs in git, and what follow-up the salon site still needs.

## What data MuttMetrics is expected to store

### Owner data
- Name
- Phone number
- Email address
- Area or district
- Preferred contact channel
- Client-since date
- Internal notes

### Pet data (dogs, cats, …)
- Pet name
- Species and breed / mix
- Weight and size-related information
- Coat and temperament fields
- Medical / grooming-risk notes that matter operationally

### Visit data
- Visit date
- Booked vs actual service
- Condition / matting score
- Actual duration
- Quoted vs actual pricing fields
- Notes about what happened during the groom

### Photos
- Intake photos
- After photos
- (later) a profile photo per dog

Photos are sensitive operational data, not marketing assets by default. Since [#30](https://github.com/BOYSABIO/muttmetrics/issues/30) they are stored as files under `PHOTO_ROOT` (outside the repository) with one metadata row per file in the `photo` table. Operational detail: [`ops-photos.md`](../runbooks/photos.md); design rationale: [ADR-002](./adr/002-photo-storage.md).

## Where the data lives (#93)

| Copy | Where | Who can reach it |
|---|---|---|
| **Live** database + photos | The home server, a box at the maintainer's home: Postgres on its localhost; photos under `/srv/muttmetrics/photos` (owner-only) | The app, through the API. The groomer reaches the app **only over Tailscale**, on one port. Nothing is exposed to the internet: no port forwarding, Tailscale Funnel off |
| Nightly backups | Same box, `/srv/muttmetrics/backups` (owner-only files) | The maintainer, over SSH (key only) |
| Off-site copy | An encrypted (LUKS) drive kept outside the house ([#221](https://github.com/BOYSABIO/muttmetrics/issues/221), pending) | Whoever holds the drive *and* the passphrase |
| The dev PC | **Synthetic data only**, once [#222](https://github.com/BOYSABIO/muttmetrics/issues/222) is done. Until then it holds a stopped copy from before the move, plus the old data folder as the only copy on another disk | The maintainer |

**Never in a cloud service.** The box's system disk isn't encrypted (it has to reboot unattended); the copy that leaves the house is the one that's encrypted. Real data is looked at on the box, read-only for analysis ([#33](https://github.com/BOYSABIO/muttmetrics/issues/33)), not copied to the dev PC.

## Git rules

These rules are non-negotiable:

- Never commit real client CSVs
- Never commit production database dumps
- Never commit exported reports that contain owner PII
- Never commit photo directories containing real client dogs
- Never commit real service prices or price floors - they live in `data/private/pricing.json`
- Never commit `.sql` scripts containing real owner, dog, or visit rows

Current git protections already help:

- `data/private/` is ignored
- `data/exports/` is ignored
- common database dump formats are ignored
- `.env` files are ignored

That reduces risk, but it does not replace judgment. A file can still contain personal data even if its name looks harmless.

## CI and test data

Only synthetic fixtures belong in the repository and CI.

- Fake names
- Fake phone/email values
- Fake visit records
- No real dog photos

If a test needs realistic structure, imitate the shape of the data, not the real data itself.

## Retention stance for v1

This is the working product stance until a fuller operational policy exists:

- Visit rows are business records and may need longer retention
- Owner contact data should be kept only as long as it supports the salon relationship
- Photos should have a shorter retention window than visit facts unless there is a clear operational reason to keep them

The exact retention periods can be refined later, but the design principle is simple: keep the minimum useful data for the minimum useful time.

## Photos: what is stored, for how long, and how it is deleted

### What reaches the disk

Every upload is decoded, rotated according to its EXIF orientation tag, **stripped of all metadata**, downscaled (long edge ≤ 1600px) and re-encoded as JPEG. That means **GPS coordinates, capture timestamps and device identifiers never reach storage** — which matters because the groomer currently travels to clients, so an untouched phone photo can carry a client's home address.

Nothing about the dog, owner or visit appears in the filename; the path is date plus a random identifier, and the database answers everything else.

### Retention

**No automatic purge.** Photos are the only material a future condition-scoring model ([#42](https://github.com/BOYSABIO/muttmetrics/issues/42)) could ever learn from, so a timed deletion would quietly destroy the dataset before there is a decision to make about it.

- Photos are kept while the client relationship is active
- They are **deleted on request** (below)
- Storage use is reviewed when it becomes a problem, not on a timer
- This stance is revisited if the salon's own privacy policy requires a fixed window

### Deletion on request

A client asking for their photos to be deleted is a request that must be honoured, not a feature request. The procedure is in [`ops-photos.md`](../runbooks/photos.md) §5 and comes down to:

```bash
python ops/photo_purge.py --owner-id <id>           # review
python ops/photo_purge.py --owner-id <id> --apply   # delete
```

Files are removed first, then rows.

### The three copies, stated honestly

"Deleted" has to mean something specific, so:

| Copy | When it goes |
|------|--------------|
| The file under `PHOTO_ROOT` and its `photo` row | immediately, when the purge runs |
| Database backup copies ([#95](https://github.com/BOYSABIO/muttmetrics/issues/95)) | **within 14 days** (daily tier), or **within 8 weeks** if the row was in a retained Sunday dump |
| Photo backup copies | **immediately**, as a step of the purge procedure — the photo backup is additive and never expires on its own ([`backup.md`](../runbooks/backup.md) §6) |
| A browser cache on a device that displayed the photo | within one hour (`Cache-Control: private, max-age=3600`) |

Telling a client the deletion is instant and total would be false. What is true and defensible: the live copy and the photo backup go immediately, and any database backup still holding their rows is gone within 14 days (8 weeks at the outside, if a retained Sunday dump is involved).

### Access

Photos are served only through the API and require the shared `X-API-Key`. The browser never holds that key ([#194](https://github.com/BOYSABIO/muttmetrics/issues/194)): Caddy on the home server ([#93](https://github.com/BOYSABIO/muttmetrics/issues/93)), or Vite's `/api` proxy in dev, adds it when forwarding. Anyone who can open the SPA can still *use* the API through that proxy — access control is the Tailscale ACL, not the key. A public deployment still needs a real auth decision ([#83](https://github.com/BOYSABIO/muttmetrics/issues/83)).

### API key (server-side only)

`API_KEY` lives in the repo-root `.env` (on the home server: `/opt/muttmetrics/.env`, mode 600, generated there). The SPA calls relative `/api/…` URLs with **no** `X-API-Key`. Caddy (production) and Vite `dev` / `preview` read `API_KEY` (never a `VITE_` name: those get baked into `dist/`) and **replace** the header on the proxy hop, so a visitor can't supply their own. Direct `:8000` callers (curl, `/docs`) still send the header themselves.

| | Holds the key | Can call the API |
|---|---|---|
| Browser / `frontend/dist` | No | Yes, via the proxy (Tailscale ACL is the gate) |
| Caddy on the home server / Vite in dev | Yes | Forwards with the header |
| FastAPI process | Yes | Enforces the header |

Rules:

- **Never put the key in a `VITE_` env var** or anywhere the SPA imports. CI runs `npm run check:no-key-in-dist` after build.
- **Don't reuse the key** anywhere else. It is a door code for this API, not a password.
- **Don't ship the example:** the API and the Vite proxy both refuse `dev-change-me` or keys shorter than 24 characters ([#187](https://github.com/BOYSABIO/muttmetrics/issues/187)).
- **Rotating it:** on the box, change `API_KEY` in `.env`, then `sudo systemctl restart muttmetrics-api caddy` (in dev: restart the API and Vite). No SPA rebuild.
- **Hosting `dist/` alone is not enough:** a static host without a proxy that injects the header cannot talk to a keyed API — and must still stay off the public internet until [#83](https://github.com/BOYSABIO/muttmetrics/issues/83).

## Client access and erasure (#195)

Under the GDPR a client can ask **what you hold** (Art. 15) and ask for it to be **erased** (Art. 17). Ops tooling (not a self-serve UI — [#143](https://github.com/BOYSABIO/muttmetrics/issues/143)):

| Request | Command | Runbook |
|---------|---------|---------|
| Access / export | `python ops/client_export.py --owner-id N` | [`client-requests.md`](../runbooks/client-requests.md) |
| Erasure | `python ops/client_erase.py --owner-id N` then `--apply` | same |

Exports land under gitignored `data/exports/` — never commit them.

### Erasure decision: anonymise, do not hard-delete

**Chosen for this salon (#195):** scrub identity, keep visit **facts**.

| Gone from the live DB | Kept (anonymous) |
|-----------------------|------------------|
| Owner name → `Erased client #{id}`; phone, email, notes, area, channel, client-since | Owner row id (FK graph) |
| Pet name → `Erased pet #{id}`; temperament / mobility / vet notes; fear-trigger free text | Species, breed ids, weight, coat/handling scores, size band |
| All photos (files + rows via `photo_purge`) | — |
| Visit free text (`what_surprised_me`, `pivot_reason`) | Visit date, minutes, prices, services, condition scores, predictions |

**Why not hard-delete:** visits are the business record and the training history for M7. Bookkeeping and an anonymous model both need those rows. Anonymise leaves no name/phone/email/notes/photos while preserving useful structure.

**Order:** photos first (files then rows), then DB scrub in one transaction. Idempotent: a second erase is a safe no-op.

**Backups:** database dumps still hold the pre-erase PII until they age out of the retention window (daily ≤14 days, retained Sundays ≤8 weeks). Photo backup copies under `BACKUP_ROOT` must be removed as part of the photo purge procedure ([`backup.md`](../runbooks/backup.md) §6). Do not rewrite old dumps. Tell the client the live copy is gone; residual backup copies expire on that schedule.

## Public-site follow-up

If the salon’s public website or any salon-owned property references or feeds this system, the salon's Datenschutzerklärung must eventually mention:

- what data is collected
- why it is collected
- where photos fit into the workflow
- how a client can ask about their data

That is website/privacy-policy work, not a blocking product feature for MuttMetrics.

## What this document does not solve

- It does not replace legal review
- It does not define every future policy edge case (e.g. a regulator-ordered hard delete of visit facts would be a new written decision)

It does make privacy explicit early, so the repo and product do not drift into bad habits by accident.
