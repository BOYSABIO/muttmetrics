# Ops: maintainer enrichment playbook

How to **fix and enrich** rows after thin capture without corrupting derived fields ([ADR-001](../architecture/adr/001-derived-fields.md)).

## Preferred path: Directory (SPA)

**Use the app.** Open the SPA home (client list) → tap a dog card (or **Owner**) → edit hand-entered fields → **Save**. Breed, sex, coat, and handling use named selects from the catalog / ADR-001-safe lists (no raw ids or magic strings). Tap **+** (or **Start visit** on a dog profile) for visit capture.

That path uses `GET`/`PATCH` for dogs and owners ([#131](https://github.com/BOYSABIO/muttmetrics/issues/131), [#132](https://github.com/BOYSABIO/muttmetrics/issues/132), UI [#138](https://github.com/BOYSABIO/muttmetrics/issues/138)–[#140](https://github.com/BOYSABIO/muttmetrics/issues/140); epic [#117](https://github.com/BOYSABIO/muttmetrics/issues/117)). Visits stay thin capture; Directory is profiles + safe edits (hand backfill when there was never Excel).

**OpenAPI** at `http://127.0.0.1:8000/docs` is a maintainer test console for the same endpoints — not the groomer UI. Authorize with `X-API-Key` first.

Connect for SQL escape-hatch work: [`ops-db-peek.md`](./db-peek.md). Schema: [`schema.md`](../architecture/schema.md). Product split: [`vision.md`](../product/vision.md).

**Audience:** Owner (maintainer); groomer may use Directory offline. Do **not** stuff CRM fields into the visit form.

### When to use what

| Path | Use when |
|------|----------|
| **Visits (SPA)** | Mid-groom / post-groom: create the visit row |
| **Directory (SPA)** | Browse/edit dog or owner hand-entered fields — **default enrichment** |
| **SQL recipes (below)** | Escape hatch: bulk fixes, edge cases, visit fact corrections, or API down |
| **Insights / analytics UI** | Later ([#130](https://github.com/BOYSABIO/muttmetrics/issues/130)) — not enrichment |

## Golden rules (Directory and SQL)

1. Only edit **hand-entered** columns (see cheat sheet). Directory PATCH already refuses derived fields; SQL must follow the same list.
2. Prefer Directory for one-off dog/owner enrichment.
3. For SQL: **SELECT before UPDATE** — confirm the id; **UPDATE by primary key**; **SELECT after UPDATE**.
4. **Never UPDATE derived columns** (owner/dog aggregates) or visit **system-computed** columns (`days_since_last`, `predicted_min_p50`, `predicted_min_p90`).
5. **No real PII in git** — scripts use placeholders (`123`, `'Example'`). Edit locally; use `ops/**/*.local.sql` if you want a personal copy (gitignored pattern: `ops/*.local.sql`).

### Safe vs forbidden (cheat sheet)

| Table | Safe to hand-UPDATE (examples) | Forbidden |
|-------|----------------------------------|-----------|
| `owner` | `phone`, `email`, `notes`, `address_area`, `preferred_channel`, `client_since`, `locale`, `name` | `visit_count`, `neglect_rate`, `lifetime_value`, … |
| `dog` | `breed_id`, `breed_secondary_id`, `weight_kg`, coat/temperament/medical hand-entered fields, `name` | `size_band`, `visit_count`, `last_visit_date`, `avg_duration_min`, … |
| `visit` | `visit_date`, `actual_minutes`, `condition_score` (**0 = worst … 5 = best**), `what_surprised_me`, `status`, service ids / prices / tips if needed | `days_since_last`, `predicted_min_p50`, `predicted_min_p90` |

Why forbidden matters: derived values are **meant to be recomputed from visits**. If you type `last_visit_date` by hand, it can disagree with the real `visit` table. Later analytics will trust the wrong number.

Directory does **not** PATCH visits yet — use SQL recipe `update_visit.sql` (or a later visit editor) for visit fact fixes.

## SQL escape hatch

Use when Directory is the wrong tool (bulk, visit patches, offline DB).

### Workflow

```text
1. Peek / find ids   →  SELECT …
2. Open script       →  ops/sql/enrich_*.sql or update_*.sql
3. Replace placeholders
4. Run SELECT block
5. Run UPDATE block
6. Run verify SELECT
```

### Recipes (explained)

Each recipe has a matching file under [`ops/sql/`](../../ops/sql/). Index: [`ops/README.md`](../../ops/README.md). Open in the Postgres extension and run section by section.

#### 1. List breeds — `lookup_breeds.sql`

**What it does:** Reads the seeded breed catalog so you know which `breed_id` to attach to a dog.

**Why:** Capture often leaves `breed_id` NULL. Cold-start priors for duration live on `breed`. Prefer setting breed in Directory when you can.

```sql
SELECT breed_id, name_de, name_en, base_groom_minutes, matting_risk
FROM breed
ORDER BY name_de;
```

#### 2. Set a dog’s breed — `enrich_dog_breed.sql`

**What it does:**

1. Finds the dog (and owner name) so you confirm the right `dog_id`.
2. Sets `breed_id` (and optionally `breed_secondary_id` for mixes).
3. Re-reads the dog with breed names joined.

**Why `JOIN breed`:** Humans read names; the DB stores ids. The join is only for display — the UPDATE still writes the integer FK.

**Do not set** `size_band` here. If you later set `weight_kg`, a future recompute job owns `size_band`.

#### 3. Fix / enrich a visit — `update_visit.sql`

**What it does:** Corrects event facts already saved (wrong minutes, date, condition, notes, status, money/service).

**Why:** Timer mistakes and “forgot to type surprise” should not require a second fake visit row. Not available in Directory UI yet.

**Photos:** do not patch URLs on `visit`. Use the photo API / [`photos.md`](./photos.md) / `photo_purge.py`.

#### 4. Enrich an owner — `update_owner.sql`

**What it does:** Adds contact / notes / area after the fact. Prefer Directory owner profile when editing one client.

#### 5. Enrich a dog (non-breed fields) — `update_dog.sql`

**What it does:** Optional coat / temperament / weight / medical notes. Prefer Directory dog profile for single-dog edits. Comment out lines you do not need — never blank-update columns you meant to leave alone.

### Finding ids quickly

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

- Recompute-derived CLI
- Pet-owner self-serve accounts (icebox [#143](https://github.com/BOYSABIO/muttmetrics/issues/143))
- Predictions / salon insights home ([#130](https://github.com/BOYSABIO/muttmetrics/issues/130))
- Visit PATCH in the SPA (still SQL for now)

HTTP `PATCH` for dog/owner obeys the same safe vs forbidden columns as this playbook ([ADR-001](../architecture/adr/001-derived-fields.md)).

## Related

- Epic: [#117](https://github.com/BOYSABIO/muttmetrics/issues/117) — Visits vs Directory
- Synthetic junk cleanup: `ops/sql/cleanup_synthetic_clients.local.sql` *(local only, gitignored: it names real rows to protect)*
- Peek starters: [`ops-db-peek.md`](./db-peek.md)
