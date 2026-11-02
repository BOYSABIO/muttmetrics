# Architecture Decision Record

## ADR-004: One `pet` table + `species` (cats now, more species later)

- **Status:** Accepted
- **Date:** 2026-11-02
- **Context:** Every animal is a `dog`: table, `/dogs`, dog breeds, dog kg → size band, dog priors. The groomer also grooms cats. Logging a cat as a dog would put a ~4 kg cat in the same size band as a Yorkshire terrier and train M7 on mixed-species noise. [#190](https://github.com/BOYSABIO/muttmetrics/issues/190) is the second species — the cheap time to generalise. A third species (rabbit, …) should be data + CHECK, not a new table of FKs.

### Decision

**One animal entity named `pet`, discriminated by `species`. Not a `cat` table. Not a product rebrand.**

1. **Table `pet`** (renamed from `dog`). PK `pet_id`. `visit.pet_id` and `photo.pet_id` follow. API is `/pets`. The lying name `dog` for “any animal” is worse than one live rename while #190 already rewrites those surfaces.

2. **`species` on `pet`, `breed`, and optionally `service`.** Allowed values live in **one Python constant** (`ALLOWED_SPECIES`) and a matching Postgres CHECK. First values: `dog`, `cat`. Default for existing rows and create-without-field: `'dog'`. `service.species` is **NULL = all species** (nails apply to both; a dog-only full-groom SKU can be tagged later).

3. **Breed must match pet species** (API 422). A Maine Coon on a dog row is the same class of lie as a cat scored on dog kg bands.

4. **Size band is species-aware.** Same letters `s|m|l|xl` (the duration prior already multiplies those). **Different kg cutoffs per species.** Dog cutoffs stay ([#171](https://github.com/BOYSABIO/muttmetrics/issues/171)). Cat cutoffs are **provisional** (below) until the groomer confirms.

5. **Metrics mix species** until a filter would change a decision. Do not hide cats from €/hour; do not pretend a cat cell is a dog cell. Filter is a later issue, not this ADR.

6. **Product name stays MuttMetrics.** `pet` is schema honesty, not a rebrand. MagicDNS, repo, and salon-facing copy can keep the current brand until a real rename is decided (iceboxed separately).

### Provisional cat size bands

Confirm / amend with the groomer; change the constant in `priors/size.py` and this table together.

| Band | Cat weight (inclusive top) | Rough meaning |
|------|----------------------------|---------------|
| `s` | ≤ 4.0 kg | Small / typical female DSH |
| `m` | ≤ 5.5 kg | Typical adult |
| `l` | ≤ 7.5 kg | Large DSH / heavy |
| `xl` | > 7.5 kg | Maine Coon / giant |

Dog (unchanged): `s` ≤ 10, `m` ≤ 26, `l` ≤ 45, else `xl`.

Unknown species → treat as dog bands only if we must; production code must pass `species` (default `'dog'`).

### How to add a species later (e.g. rabbit)

1. Add the slug to `ALLOWED_SPECIES` and the CHECK (one migration).
2. Seed breeds (and timings) for that species.
3. Optional: kg → band table in `priors/size.py` (omit = no size multiplier, same as unknown weight).
4. Optional: tag services that do not apply (`service.species`).
5. SPA picker gains a chip. No new table, no new FK on `visit`.

### When a product rebrand *would* be worth it

Table/API are already `pet`. A **MuttMetrics → PetMetrics** rename is brand/domain/MagicDNS only — not schema. Do it if/when owner-facing surfaces ([#38](https://github.com/BOYSABIO/muttmetrics/issues/38), [#41](https://github.com/BOYSABIO/muttmetrics/issues/41)) or a second salon make the vendor name wrong. Until then, icebox ([#209](https://github.com/BOYSABIO/muttmetrics/issues/209)). Dashboard species filter: [#210](https://github.com/BOYSABIO/muttmetrics/issues/210).

### Consequences

- Capture asks dog vs cat; Directory shows species; breed/service pickers filter.
- Existing salon rows stay `species = 'dog'`; tests and Syn* fixtures keep working as dogs.
- Adding “lemur” is a CHECK + seed, not a `lemur` table.

### Alternatives considered

- **`cat` table (or per-species tables):** rejected. Visit/photo FKs, search, Directory, priors, and GDPR export would fork forever.
- **Keep table `dog` + `species` column only:** rejected for this issue. Accurate, but every #190 file would be renamed again later. One `RENAME` now, data preserved.
- **No size band for cats:** honest if we have no kg scale; we would rather ship a labelled-provisional scale than score cats on dog thresholds.
- **Rename the product in the same PR:** rejected; different decision, different blast radius.
