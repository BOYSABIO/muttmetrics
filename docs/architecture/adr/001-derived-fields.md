# Architecture Decision Record

## ADR-001: Derived fields as stored columns (recomputed), not views

- **Status:** Accepted (amended 2026-10-16 for [#171](https://github.com/BOYSABIO/muttmetrics/issues/171))
- **Date:** 2026-08-27
- **Context:** Local design notes mark many `owner` and `dog` fields as DERIVED — recomputed from visit history, never hand-entered. Before SQLAlchemy models and Alembic migrations (issues #7–#8), we must choose whether those fields are real columns, SQL views, or compute-on-read only. That choice changes the schema, the capture API, and how safe our training labels stay.

### Decision

Three entities, two kinds of “not typed by the groomer”:

- **`owner` / `dog`:** rolling snapshots of visit history. Store as **nullable columns**, **recompute via a job/CLI** after visits change. Never accept them as user input on APIs or CSV import.
- **`visit`:** the **fact table** (one row per groom). Most fields are captured at the event. A small set is **system-computed at write/score time** and stored on that row — not a later aggregate job.

`dog.size_band` is derived from `weight_kg`; store it, recompute when weight changes.

### Amendment (#171) — two kinds of “derived,” handled differently

A stored aggregate is a **cache**. Until #171, the recompute job from this ADR never shipped, so caches like `last_visit_date` and `size_band` stayed `NULL` while product code still read them. Fix:

| Field | Depends on | Approach after #171 |
|-------|------------|---------------------|
| `last_visit_date`, `visit_count` (dog + owner) | Visit history | **Compute on read** from `visit` rows with the shared status rule (`completed` or `NULL`). Columns may stay for a future job; product paths must not read them. |
| `size_band` | The dog’s own `weight_kg` | **Pure function** `size_band_from_weight` for the prior and profile display; **write-through** on dog PATCH when `weight_kg` changes; one-time backfill (`ops/backfill_size_band.py`) for dogs that already have a weight. |

Other ADR-001 dog/owner aggregates (`avg_duration_min`, owner LTV, …) stay `NULL` until a real recompute job exists — nothing reads them for metrics or the prior today.

### Hand-entered vs derived

#### `owner` — hand-entered

`name`, `phone`, `email`, `locale`, `address_area`, `preferred_channel`, `client_since`, `notes`

#### `owner` — derived (columns; recompute only)

`visit_count`, `avg_rebook_days`, `neglect_rate`, `cancellation_rate`, `no_show_count`, `avg_tip_pct`, `lifetime_value`, `reliability_score`

#### `dog` — hand-entered

`owner_id`, `name`, `breed_id`, `breed_secondary_id`, `sex`, `date_of_birth`, `weight_kg`, coat fields (`coat_type`, `hair_or_fur`, `coat_density`, `undercoat`, `sheds`), temperament fields (`handling_score`, `fear_triggers`, `muzzle_required`, `two_person_job`, `temperament_notes`), medical fields (`skin_conditions`, `senior_flag`, `mobility_notes`, `vet_notes`)

#### `dog` — derived (columns; recompute only)

`size_band` (from `weight_kg`), `visit_count`, `avg_duration_min`, `duration_stddev_min`, `typical_interval_days`, `last_visit_date`, `next_due_date`

#### `visit` — captured at the event (hand-entered or observed)

`dog_id`, `owner_id`, `visit_date`, `booked_service_id`, `booking_channel`, `is_emergency`, `quoted_price`, `condition_score`, `matting_locations`, `fleas_or_parasites`, `arrived_wet_dirty`, `actual_service_id`, `pivoted`, `pivot_reason`, `shaved_down`, `actual_minutes`, `final_price`, `tip`, `what_surprised_me`, `behaviour_this_visit`, `status`, `cancelled_hours_before`. Techniques are rows in `visit_add_on` ([#192](https://github.com/BOYSABIO/muttmetrics/issues/192)), not a column on `visit`.

(`pivoted` may be set from `booked_service_id != actual_service_id` in code; it is still an event fact on the row, not a rolling owner/dog aggregate.)

**Amendment (2026-10-02, #98):** `intake_photos` / `after_photos` removed from the capture contract; photos are `photo` rows only.

#### `visit` — system-computed at write/score time (stored on the row; not hand-entered)

`days_since_last` (from this dog’s previous visit date), `predicted_min_p50`, `predicted_min_p90`

These are **not** filled by the owner/dog recompute job. They are written when the visit is created or scored. `actual_minutes` stays the training label; predictions sit beside it so calibration is honest from row one.

### Consequences

- Models issue (#7) includes derived columns on `owner` / `dog` as normal mapped attributes, nullable where history is missing; `visit` includes the system-computed columns above.
- Capture, CSV import, and any later HTTP `PATCH` for dog/owner must not silently overwrite owner/dog derived columns, or visit `days_since_last` / `predicted_*`, from user input. Same safe lists as the enrichment runbook. `#171`: PATCH may **write** `size_band` when `weight_kg` changes — still never accept `size_band` from the client.
- A `recompute_derived` CLI is part of the design (later issue on M2–M3), even if not built in this ADR. Until then, visit-history fields used in product are compute-on-read (#171).
- Analytics can still aggregate over `visit` when they need guaranteed freshness; visit-history product reads do the same. `size_band` is write-through + optional backfill, not a visit aggregate.

### Alternatives considered

- **SQL views / compute-on-read only:** always fresh; poorer ORM ergonomics; harder to index simple filters (e.g. high `neglect_rate`) without materialized views; easy to blur “input” vs “output” in application code.
- **Materialized views refreshed on a schedule:** valid later if recompute logic gets heavy; more Postgres ops than we want for v1.
- **No derived storage until n is large:** forces every prior/API to re-aggregate; duplicates logic across call sites.

### Follow-ups

- Models (#7) and migrations (#8) must match this split.
- Import templates: derived columns absent or ignored.
- Link this ADR from issue #7 before implementing models.
