# Case study: building a data layer for a business that had none

> A write-up of why MuttMetrics exists, how it was approached, and what a real field trial changed. Setup and code are in the [README](../README.md). The product framing is in [`VISION.md`](./VISION.md).
> Business details are left general on purpose: the salon isn't named, and nothing here identifies a client, a dog or an owner.

---

## The problem

A single-groomer salon runs its day on a guess. How long a groom takes depends on things that only show up when the dog is on the table: coat condition, matting, temperament, how long it's been since the last visit. The same breed and the same service can take 60 minutes one week and two hours the next.

The salon protects itself the usual way. It caps the number of dogs per day and leaves slack for the bad cases. That slack is a **variance tax**: capacity paid for every day to cover an overrun that only sometimes happens.

The information that could shrink that tax already exists, but it lives in the groomer's head. There were no structured records, no timings and no history per dog. So there was nothing to predict from.

## The constraint that shaped everything

The obvious fix is "start keeping records." The reason that usually fails decides the whole design:

- **The groomer's hands are busy.** A groom runs one to two hours with a live animal on the table. Anything that needs attention *during* the work won't get it.
- **No evening homework.** Filling in a spreadsheet after a full day of grooming is the step every records system quietly dies on.
- **The data is sensitive.** Client contact details, addresses and photos of people's pets are personal data, and they can't end up in a public repo or a careless backup.

So the question wasn't "what schema would be ideal?" It was **"what can realistically be captured at the moment of the groom, and how do we build everything else on top of that?"**

## The approach: capture first

**1. Start from an empty database and grow it row by row.** No historical import. Each completed groom becomes a `visit` row, entered on the groomer's phone browser in the shop. If the rows don't get written, nothing else matters, so capture compliance is the product gate.

**2. Let capture design drive the schema, not the reverse.** The `visit` table is the fact table, and its one mandatory label is `actual_minutes`, the thing everything later tries to predict. Columns are split by where they come from ([ADR-001](./adr/001-derived-fields.md)):
- **hand-entered** at the groom, kept short;
- **system-computed at write** (e.g. days since the last visit);
- **derived** by recompute jobs (visit counts, average duration, typical rebook interval).

The groomer only ever sees the first group.

**3. Thin capture, then enrichment.** The phone form asks for the minimum. Richer detail (coat, temperament notes, medical flags) is added afterwards through a documented enrichment workflow. That keeps the on-the-job form fast without giving up the depth later analysis needs.

**4. Honest priors before any model.** The first prediction target is a *range* (P50/P90) from rules and reference priors per breed and service, with prediction error logged from day one. A fitted model only replaces the rules once there's enough data to beat them.

**5. Privacy by construction.** Photos are stored as files outside the repository, with only metadata in Postgres ([ADR-002](./adr/002-photo-storage.md)). Every upload is decoded, rotated, **stripped of EXIF** (no GPS coordinates from a phone ever reach disk), downscaled and re-encoded. Deletion is deliberate application code, not a database cascade, so files are never stranded or silently kept.

**Stack:** Python · Postgres · SQLAlchemy · Alembic · FastAPI, with a Vite + React + TypeScript phone app for capture. It started as a thin server-rendered form and was retired once the SPA proved itself.

## The field trial

The design was only a hypothesis until the groomer used it. So the test was simple: **the groomer runs a real groom through the app on their own phone, with no help.**

It worked. The first visit row not entered by the builder went into the database. The trial also did its real job and surfaced three specific failures that no amount of desk testing had caught:

| What the trial exposed | Why it mattered | Fix |
|---|---|---|
| A failed save showed a generic *"Network error"* with no hint whether the visit was stored | A groomer who can't tell if their work was saved doesn't file a bug report. They stop using the tool | Errors now say what actually happened ([#87](https://github.com/BOYSABIO/muttmetrics/issues/87)) |
| The groom timer died if the phone discarded the browser tab mid-groom | Duration **is** the product. Lose the timer and the one label that matters is gone | The in-progress visit now persists and survives a killed tab ([#88](https://github.com/BOYSABIO/muttmetrics/issues/88)) |
| Photos were a "paste a URL" field | Nobody working a groom pastes URLs. Photos live in the camera roll | Real photo storage built ([#30](https://github.com/BOYSABIO/muttmetrics/issues/30)), with phone upload next ([#92](https://github.com/BOYSABIO/muttmetrics/issues/92)) |

All three were fixed within days of the trial.

## An outside signal

At an industry trade show, one exhibitor showed a grooming product built around metrics and AI. It drew a lot of interest, and then it missed. The feedback from people who groom for a living came down to one line:

> *Groomers already know how to groom. That's not the problem.*

What they wanted was something that fits into the work without friction, keeps the records, and gives back insight without the hassle. **That's the capture-first thesis, tested by someone else in front of the actual customers.** The interest in the category was real. What failed was an approach that asked the groomer to change how they work.

## Where it stands

- **Capture is running on real grooms**, and rows are accumulating.
- **Current work:** enriching the captured rows and finishing the capture surface (photo upload, scheduled backups) **until the groomer can capture completely on their own.**
- **Next:** duration ranges from the captured data, then turning those ranges into day-planning decisions. The question becomes *"can I take one more dog today?"* answered against summed P90s instead of a fixed daily cap.

## Direction

The long-term idea is an **intelligence layer on data the business owns**: capacity and pricing decisions grounded in how long work actually takes, rather than yet another salon management suite. Whether that stays a tool for one shop or grows into something broader is left open on purpose. **The single-shop loop has to prove itself first.**

## What this project taught

- **Design for the moment of capture.** The schema, the UI and the rollout all follow from "what can a busy person enter in a few seconds, on a phone, mid-job?"
- **Protect the label.** In a prediction system, the one field you're predicting is the thing to defend hardest. The worst bug the trial found was the one that could silently lose it.
- **A field trial beats a spec.** One real groom produced three concrete defects that weeks of building hadn't.
- **Silent failure is worse than no feature.** Users don't report confusing errors. They quietly stop using the tool.
- **Treat privacy as architecture, not policy.** Where photos live, what metadata survives, and how deletion works are all design decisions, made before real data arrived.
