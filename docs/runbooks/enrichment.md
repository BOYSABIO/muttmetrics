# Ops: maintainer enrichment playbook

How to **fix and enrich** rows after thin capture without corrupting derived fields ([ADR-001](../architecture/adr/001-derived-fields.md)).

**Preferred path (shipping under [M4.75](https://github.com/BOYSABIO/muttmetrics/milestone/14) / epic [#117](https://github.com/BOYSABIO/muttmetrics/issues/117)):** SPA **Directory** — Visits stay thin capture; Directory is profiles + safe edits (hand backfill when there was never Excel). Children: [#131](https://github.com/BOYSABIO/muttmetrics/issues/131) read API → [#132](https://github.com/BOYSABIO/muttmetrics/issues/132) PATCH → [#138](https://github.com/BOYSABIO/muttmetrics/issues/138) shell → [#139](https://github.com/BOYSABIO/muttmetrics/issues/139)/[#140](https://github.com/BOYSABIO/muttmetrics/issues/140) profiles → [#141](https://github.com/BOYSABIO/muttmetrics/issues/141) docs. Until that UI is usable, use the SQL recipes below.

Connect first: [`ops-db-peek.md`](./db-peek.md). Schema overview: [`schema.md`](../architecture/schema.md). Product split: [`vision.md`](../product/vision.md).

**Audience:** Owner (maintainer). Groomer’s visit SPA stays thin on purpose — do not stuff CRM fields into the visit form.

### When to use what

| Path | Use when |
|------|----------|
| **Visits (SPA)** | Mid-groom / post-groom: create the visit row |
| **Directory (SPA)** | Browse/edit dog or owner hand-entered fields; preferred enrichment once M4.75 lands |
| **SQL recipes (this playbook)** | Escape hatch: bulk fixes, edge cases, or Directory not ready yet |
| **Insights / analytics UI** | Later ([#130](https://github.com/BOYSABIO/muttmetrics/issues/130)) — not enrichment |

## Golden rules

1. **SELECT before UPDATE** — see the row; confirm the id.
2. **UPDATE by primary key** (`owner_id`, `dog_id`, `visit_id`) — not by name alone (duplicate names exist).
3. **SELECT after UPDATE** — verify.
4. **Never UPDATE derived columns** (owner/dog aggregates) or visit **system-computed** columns (`days_since_last`, `predicted_min_p50`, `predicted_min_p90`).
5. **No real PII in git** — scripts use placeholders (`123`, `'Example'`). Edit locally; use `ops/**/*.local.sql` if you want a personal copy (gitignored pattern: `ops/*.local.sql`).

### Safe vs forbidden (cheat sheet)

| Table | Safe to hand-UPDATE (examples) | Forbidden |
|-------|----------------------------------|-----------|
| `owner` | `phone`, `email`, `notes`, `address_area`, `preferred_channel`, `client_since`, `locale`, `name` | `visit_count`, `neglect_rate`, `lifetime_value`, … |
| `dog` | `breed_id`, `breed_secondary_id`, `weight_kg`, coat/temperament/medical hand-entered fields, `name` | `size_band`, `visit_count`, `last_visit_date`, `avg_duration_min`, … |
| `visit` | `visit_date`, `actual_minutes`, `condition_score` (**0 = worst … 5 = best**), `what_surprised_me`, `status`, service ids / prices / tips if needed | `days_since_last`, `predicted_min_p50`, `predicted_min_p90` |

Why forbidden matters: derived values are **meant to be recomputed from visits**. If you type `last_visit_date` by hand, it can disagree with the real `visit` table. Later analytics/M4 will trust the wrong number. There is no DB “formula” that auto-fixes that — you just created a lie that looks official.

## Workflow (every enrichment)

```text
1. Peek / find ids   →  SELECT …
2. Open script       →  ops/sql/enrich_*.sql or update_*.sql
3. Replace placeholders
4. Run SELECT block
5. Run UPDATE block
6. Run verify SELECT
```

## Recipes (explained)

Each recipe has a matching file under [`ops/sql/`](../../ops/sql/). Index of all scripts: [`ops/README.md`](../../ops/README.md). Open the file in the Postgres extension and run section by section.

### 1. List breeds — `lookup_breeds.sql`

**What it does:** Reads the seeded breed catalog so you know which `breed_id` to attach to a dog.

**Why:** Capture often leaves `breed_id` NULL. Cold-start priors for duration live on `breed`; enrichment starts here.

```sql
SELECT breed_id, name_de, name_en, base_groom_minutes, matting_risk
FROM breed
ORDER BY name_de;
```

### 2. Set a dog’s breed — `enrich_dog_breed.sql`

**What it does:**

1. Finds the dog (and owner name) so you confirm the right `dog_id`.
2. Sets `breed_id` (and optionally `breed_secondary_id` for mixes).
3. Re-reads the dog with breed names joined.

**Why `JOIN breed`:** Humans read names; the DB stores ids. The join is only for display — the UPDATE still writes the integer FK.

**Do not set** `size_band` here. If you later set `weight_kg`, a future recompute job owns `size_band`.

### 3. Fix / enrich a visit — `update_visit.sql`

**What it does:** Corrects event facts User already saved (wrong minutes, date, condition, notes, status, money/service).

**Why:** Timer mistakes and “forgot to type surprise” should not require a second fake visit row.

**Photos:** do not patch URLs on `visit`. Use the photo API / [`photos.md`](./photos.md) / `photo_purge.py`.

### 4. Enrich an owner — `update_owner.sql`

**What it does:** Adds contact / notes / area after the fact so capture never asked User for homework mid-groom.

### 5. Enrich a dog (non-breed fields) — `update_dog.sql`

**What it does:** Optional coat / temperament / weight / medical notes. Comment out lines you do not need — never blank-update columns you meant to leave alone.

## Finding ids quickly

```sql
-- Dogs with owners (directory-style)
SELECT d.dog_id, d.name AS dog_name, o.owner_id, o.name AS owner_name, d.breed_id
FROM dog d
JOIN owner o ON o.owner_id = d.owner_id
ORDER BY o.name, d.name;

-- Recent visits
SELECT visit_id, dog_id, owner_id, visit_date, actual_minutes, status
FROM visit
ORDER BY visit_id DESC
LIMIT 20;
```

## Out of scope (this playbook)

- Implementing Directory UI/API (that is M4.75 / [#117](https://github.com/BOYSABIO/muttmetrics/issues/117) children — not forever deferred)
- Recompute-derived CLI
- Pet-owner self-serve accounts (icebox; depends on Directory APIs)
- Predictions / M5 charts ([#130](https://github.com/BOYSABIO/muttmetrics/issues/130))

**Note:** HTTP `PATCH` for dog/owner must obey the same safe vs forbidden columns as this SQL playbook ([ADR-001](../architecture/adr/001-derived-fields.md)).

## Related

- Epic: [#117](https://github.com/BOYSABIO/muttmetrics/issues/117) — Visits vs Directory
- Synthetic junk cleanup: `ops/sql/cleanup_synthetic_clients.local.sql` *(local only, gitignored: it names real rows to protect)*
- Peek starters: [`ops-db-peek.md`](./db-peek.md)
