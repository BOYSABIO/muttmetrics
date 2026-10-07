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

### Dog data
- Dog name
- Breed / mix
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

Photos are served only through the API and require the shared `X-API-Key`. The key is embedded in the built SPA, so it is a gate against strangers on the network, **not** a secret from anyone who can open the app — which is why the capture UI is not exposed beyond the tailnet ([#82](https://github.com/BOYSABIO/muttmetrics/issues/82)) and why a public deployment needs a real auth decision ([#83](https://github.com/BOYSABIO/muttmetrics/issues/83)).

## Public-site follow-up

If the salon’s public website or any salon-owned property references or feeds this system, the salon's Datenschutzerklärung must eventually mention:

- what data is collected
- why it is collected
- where photos fit into the workflow
- how a client can ask about their data

That is website/privacy-policy work, not a blocking product feature for MuttMetrics.

## What this issue does not solve

- It does not replace legal review
- It does not implement **export** tooling (deletion tooling for photos landed with #30; owner/dog/visit export is still manual SQL)
- It does not define every future policy edge case

It does make privacy explicit early, so the repo and product do not drift into bad habits by accident.
