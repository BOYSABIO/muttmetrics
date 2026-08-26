# Privacy

MuttMetrics handles real client-adjacent business data for a German dog grooming shop. This document is not legal advice; it is the engineering checklist for what data we store, what never belongs in git, and what follow-up the salon site still needs.

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

Photos should be treated as sensitive operational data, not marketing assets by default.

## Git rules

These rules are non-negotiable:

- Never commit real client CSVs
- Never commit production database dumps
- Never commit exported reports that contain owner PII
- Never commit photo directories containing real client dogs

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

## Public-site follow-up

If `wag-the-dog.vercel.app` or any salon-owned public property references or feeds this system, the salon's Datenschutzerklärung must eventually mention:

- what data is collected
- why it is collected
- where photos fit into the workflow
- how a client can ask about their data

That is website/privacy-policy work, not a blocking product feature for MuttMetrics.

## What this issue does not solve

- It does not replace legal review
- It does not implement deletion/export tooling
- It does not define every future policy edge case

It does make privacy explicit early, so the repo and product do not drift into bad habits by accident.
