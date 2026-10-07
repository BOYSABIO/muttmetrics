# Data model

Canonical schema for MuttMetrics. SQLAlchemy models live in `src/muttmetrics/models/`; Alembic migrations (#8) will materialize this in Postgres.

**Design split:** [ADR-001](./adr/001-derived-fields.md) — hand-entered vs derived vs system-computed-at-write columns.

## Entity relationships

```mermaid
erDiagram
    OWNER ||--o{ DOG : "has"
    DOG ||--o{ VISIT : "has"
    OWNER ||--o{ VISIT : "has"
    BREED ||--o{ DOG : "breed_id"
    BREED ||--o{ DOG : "breed_secondary_id"
    SERVICE ||--o{ VISIT : "booked_service_id"
    SERVICE ||--o{ VISIT : "actual_service_id"
    DOG ||--o{ PHOTO : "has"
    VISIT ||--o{ PHOTO : "intake / after"

    OWNER {
        int owner_id PK
        text name
        text locale
        int visit_count "derived"
        numeric neglect_rate "derived"
    }

    DOG {
        int dog_id PK
        int owner_id FK
        int breed_id FK
        text name
        numeric weight_kg
        text size_band "derived"
        int handling_score "1-5 internal"
    }

    VISIT {
        int visit_id PK
        int dog_id FK
        int owner_id FK
        date visit_date
        int actual_minutes "NOT NULL label"
        int days_since_last "system-computed"
        int predicted_min_p50 "system-computed"
        int condition_score "0 worst - 5 best"
        text status "completed|cancelled|no_show"
    }

    BREED {
        int breed_id PK
        text name_de
        int base_groom_minutes
        int matting_risk "1-5 prior"
    }

    SERVICE {
        int service_id PK
        text slug UK
        int base_minutes
        numeric price_base
    }

    PHOTO {
        int photo_id PK
        int dog_id FK
        int visit_id FK "null for a profile photo"
        text kind "intake | after | profile"
        text storage_key "relative path on disk"
        text sha256
        timestamptz created_at
    }
```

**Navigation path:** `owner.dogs` → `dog.visits` (and `owner.visits` for direct owner-level queries).

## Tables

| Table | Role | Key relationships |
|-------|------|-------------------|
| `owner` | Slow-changing client (human). Behavioural aggregates. | → many `dog`, many `visit` |
| `dog` | Slow-changing physical + temperament priors per pet. | → `owner`, → `breed` (×2 for mixes), → many `visit` |
| `visit` | **Fact table** — one row per groom; training labels live here. | → `dog`, `owner`, → `service` (booked + actual) |
| `breed` | Reference priors for cold start (coat, duration, matting risk). | ← `dog.breed_id`, `dog.breed_secondary_id` |
| `service` | Reference groom types (slug, minutes, **price floor**). | ← `visit.booked_service_id`, `visit.actual_service_id` |
| `photo` | One row per stored image file. Bytes live on disk under `PHOTO_ROOT`, **not** in the database ([ADR-002](./adr/002-photo-storage.md)). | → `dog` (required), → `visit` (optional — a profile photo has no visit) |

## Column groups (by table)

### `owner`

| Group | Columns |
|-------|---------|
| Hand-entered | `name`, `phone`, `email`, `locale`, `address_area`, `preferred_channel`, `client_since`, `notes` |
| Derived (recompute job) | `visit_count`, `avg_rebook_days`, `neglect_rate`, `cancellation_rate`, `no_show_count`, `avg_tip_pct`, `lifetime_value`, `reliability_score` |

### `dog`

| Group | Columns |
|-------|---------|
| Identity | `owner_id`, `name`, `breed_id`, `breed_secondary_id`, `sex`, `date_of_birth`, `weight_kg` |
| Coat | `coat_type`, `hair_or_fur`, `coat_density`, `undercoat`, `sheds` |
| Temperament (internal) | `handling_score`, `fear_triggers[]`, `muzzle_required`, `two_person_job`, `temperament_notes` |
| Medical | `skin_conditions[]`, `senior_flag`, `mobility_notes`, `vet_notes` |
| Derived (recompute job) | `size_band`, `visit_count`, `avg_duration_min`, `duration_stddev_min`, `typical_interval_days`, `last_visit_date`, `next_due_date` |

### `visit`

| Group | Columns |
|-------|---------|
| Identity | `dog_id`, `owner_id`, `visit_date` |
| Booking | `booked_service_id`, `booking_channel`, `is_emergency`, `quoted_price` |
| System-computed at write | `days_since_last`, `predicted_min_p50`, `predicted_min_p90` |
| Intake | `condition_score` (**0 = worst … 5 = best**, or NULL), `matting_locations[]`, `fleas_or_parasites`, `arrived_wet_dirty` |
| Outcome | `actual_service_id`, `pivoted`, `pivot_reason`, `shaved_down`, `actual_minutes`, `final_price`, `tip`, `add_ons[]` |
| Qualitative | `what_surprised_me`, `behaviour_this_visit` |
| Status | `status`, `cancelled_hours_before` |

### `breed` / `service`

Reference tables only — no FKs to other entities. See model files for full column lists.

### `photo`

| Group | Columns |
|-------|---------|
| Identity | `photo_id` |
| Belongs to | `dog_id` (NOT NULL), `visit_id` (nullable), `kind` (`intake` / `after` / `profile`) |
| Where the bytes are | `storage_key` (relative, unique), `storage_backend` (default `local`) |
| What the bytes are | `content_type`, `byte_size`, `sha256` |
| When | `created_at` (timestamptz, needed for retention and the orphan sweep) |

Constraints: `kind` is checked; a `profile` photo must have no `visit_id` while `intake` / `after` must have one; `byte_size > 0`. Foreign keys deliberately have **no `ON DELETE CASCADE`** — Postgres cannot delete files, so a cascade would strand bytes on disk. Deletion goes through `ops/photo_purge.py` (see [`photos.md`](../runbooks/photos.md)).

**History:** `visit.intake_photos` / `after_photos` (`TEXT[]` of URLs) were removed in [#98](https://github.com/BOYSABIO/muttmetrics/issues/98) once the SPA wrote only to this table.

## Implementation notes

- **Arrays:** list fields use Postgres `ARRAY(Text)`, not JSON (`fear_triggers`, `matting_locations`, `add_ons`, etc.).
- **CHECK constraints** (initial migration #8): `dog.handling_score` 1–5; `visit.condition_score` 0–5; `visit.behaviour_this_visit` 1–5; `visit.status` ∈ `completed`, `cancelled`, `no_show`. Postgres rejects invalid values even if application code bugs — e.g. `condition_score = 99` fails with `ck_visit_condition_score`.
- **Scales (locked [#123](https://github.com/BOYSABIO/muttmetrics/issues/123)):** `visit.condition_score` — **0 = worst** coat / hardest job, **5 = best** / easiest, NULL = not assessed. `dog.handling_score` — **1 = easy** on the table, **5 = hardest**, NULL = unknown (rules prior treats **3** as neutral).
- **Query indexes** (migration `bba4e6f67c96`, issue #9): FK columns on `dog` and `visit`, plus `visit.visit_date` — for owner/dog listings, visit history, day packing, and service-mix queries.
- **Required columns:** `owner.name`, `dog.name`, `visit.visit_date`, `visit.actual_minutes`.
- **Service prices:** `service.price_base` is an optional catalog **floor**. Committed seed leaves it NULL; a gitignored `data/private/pricing.json` overlay fills it locally. Size bands live on `dog`; on-the-spot charge on `visit.quoted_price` / `final_price` / `tip`.
- **Migrations:** Alembic — `alembic upgrade head` applies schema. See [`CONTRIBUTING.md`](../../CONTRIBUTING.md).
- **Seed:** `python -m muttmetrics.seed` upserts breeds + services (idempotent).

### Indexes (issue #9)

| Index | Table | Column | Query path |
|-------|-------|--------|------------|
| `ix_dog_owner_id` | dog | `owner_id` | List dogs per owner |
| `ix_dog_breed_id` | dog | `breed_id` | Breed analytics |
| `ix_dog_breed_secondary_id` | dog | `breed_secondary_id` | Mix breeds |
| `ix_visit_dog_id` | visit | `dog_id` | Dog visit history; recompute dog stats |
| `ix_visit_owner_id` | visit | `owner_id` | Owner visit history; recompute owner stats |
| `ix_visit_visit_date` | visit | `visit_date` | Day view, date-range filters |
| `ix_visit_booked_service_id` | visit | `booked_service_id` | Booked service mix |
| `ix_visit_actual_service_id` | visit | `actual_service_id` | Actual outcome / pivot analysis |

## Source

| Model | File |
|-------|------|
| `Owner` | `src/muttmetrics/models/owner.py` |
| `Dog` | `src/muttmetrics/models/dog.py` |
| `Visit` | `src/muttmetrics/models/visit.py` |
| `Breed` | `src/muttmetrics/models/breed.py` |
| `Service` | `src/muttmetrics/models/service.py` |
