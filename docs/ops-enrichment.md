# Ops: Spencer enrichment playbook

How to **fix and enrich** rows after thin capture — without a CRM UI and without corrupting derived fields ([ADR-001](./adr/001-derived-fields.md)).

Connect first: [`ops-db-peek.md`](./ops-db-peek.md). Schema overview: [`schema.md`](./schema.md).

**Audience:** Spencer (maintainer). Sebastian’s SPA stays thin on purpose.

## Golden rules

1. **SELECT before UPDATE** — see the row; confirm the id.
2. **UPDATE by primary key** (`owner_id`, `dog_id`, `visit_id`) — not by name alone (duplicate names exist).
3. **SELECT after UPDATE** — verify.
4. **Never UPDATE derived columns** (owner/dog aggregates) or visit **system-computed** columns (`days_since_last`, `predicted_min_p50`, `predicted_min_p90`).
5. **No real PII in git** — scripts use placeholders (`123`, `'Example'`). Edit locally; use `scripts/**/*.local.sql` if you want a personal copy (gitignored pattern: `scripts/*.local.sql`).

### Safe vs forbidden (cheat sheet)

| Table | Safe to hand-UPDATE (examples) | Forbidden |
|-------|----------------------------------|-----------|
| `owner` | `phone`, `email`, `notes`, `address_area`, `preferred_channel`, `client_since`, `locale`, `name` | `visit_count`, `neglect_rate`, `lifetime_value`, … |
| `dog` | `breed_id`, `breed_secondary_id`, `weight_kg`, coat/temperament/medical hand-entered fields, `name` | `size_band`, `visit_count`, `last_visit_date`, `avg_duration_min`, … |
| `visit` | `visit_date`, `actual_minutes`, `condition_score`, `what_surprised_me`, `status`, `intake_photos`, prices/tips if needed | `days_since_last`, `predicted_min_p50`, `predicted_min_p90` |

Why forbidden matters: derived values are **meant to be recomputed from visits**. If you type `last_visit_date` by hand, it can disagree with the real `visit` table. Later analytics/M4 will trust the wrong number. There is no DB “formula” that auto-fixes that — you just created a lie that looks official.

## Workflow (every enrichment)

```text
1. Peek / find ids   →  SELECT …
2. Open script       →  scripts/SQL/enrich_*.sql or update_*.sql
3. Replace placeholders
4. Run SELECT block
5. Run UPDATE block
6. Run verify SELECT
```

## Recipes (explained)

Each recipe has a matching file under [`scripts/SQL/`](../scripts/SQL/). Open the file in the Postgres extension and run section by section.

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

**What it does:** Corrects event facts Sebastian already saved (wrong minutes, date, condition, notes, status, photo URL array).

**Why:** Timer mistakes and “forgot to type surprise” should not require a second fake visit row.

**Arrays:** `intake_photos` is `TEXT[]`. Example literal: `ARRAY['https://example.com/before.jpg']`.

### 4. Enrich an owner — `update_owner.sql`

**What it does:** Adds contact / notes / area after the fact so capture never asked Sebastian for homework mid-groom.

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

- PATCH HTTP APIs (add later only if SQL gets painful)
- Recompute-derived CLI
- Sebastian-facing profile editor
- Predictions / M4

## Related

- Synthetic junk cleanup: [`scripts/SQL/cleanup_synthetic_clients.sql`](../scripts/SQL/cleanup_synthetic_clients.sql)
- Peek starters: [`ops-db-peek.md`](./ops-db-peek.md)
