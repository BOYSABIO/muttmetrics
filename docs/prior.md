# Rules-based duration prior (P50 / P90)

Hand-encoded baseline for how long a groom will take, **before** any fitted model. Implemented as a pure function in [`src/muttmetrics/priors/prior.py`](../src/muttmetrics/priors/prior.py) ([#23](https://github.com/BOYSABIO/muttmetrics/issues/23)).

This doc is the formula source of truth. If code and doc disagree, fix one of them and keep them aligned.

## What P50 and P90 mean

| Symbol | Meaning (minutes) |
|--------|-------------------|
| **P50** | Middle guess — about half the time the job is this long or less |
| **P90** | Cautious guess — about nine times out of ten finished by here |

Day packing should use **P90**. P50 alone is too optimistic.

Always **P90 ≥ P50**. The gap is the uncertainty buffer.

## What “rules prior” means

- **Prior** — belief about duration before rich history for this dog exists (breed base, size, matting risk, overdue, handling).
- **Rules** — deterministic multipliers we chose and tested. Same inputs → same `(p50, p90)`.
- **On visit create** — `POST /visits` computes `days_since_last` and stores `predicted_min_p50` / `predicted_min_p90` when breed priors exist ([#24](https://github.com/BOYSABIO/muttmetrics/issues/24)); see `api/services/visit_predictions.py`.
- **Preview without a visit** ([#26](https://github.com/BOYSABIO/muttmetrics/issues/26)) — same helper via `GET /dogs/{dog_id}/duration-range` or `python -m muttmetrics.priors --dog-id N`. Optional `service_id` is validated/echoed; v0 minutes still come from breed priors.

## Function

```text
rules_prior(
  base_groom_minutes,
  matting_risk=1,                 # 1..5
  size_band=None,                 # s | m | l | xl
  days_since_last=None,
  recommended_interval_days=None,
  handling_score=None,            # 1..5; 3 = neutral
) → (p50, p90)
```

No database, no I/O. Callers pass plain values (later: loaded from breed/dog/visit).

## Formula (v0)

### Multipliers

| Factor | Rule |
|--------|------|
| **Size** | `s→0.85`, `m→1.00`, `l→1.15`, `xl→1.30`; missing → `1.00` |
| **Matting** | `1.0 + 0.10 × (matting_risk − 1)` → `1.0 … 1.4` |
| **Interval / neglect** | If both `days_since_last` and `recommended_interval_days` (>0) are set: `overdue = days_since_last / recommended_interval_days`, then `interval_mult = clamp(0.90 + 0.20 × overdue, 0.90, 1.50)`. Else `1.0`. |
| **Handling** | Missing → `1.0`. Else `clamp(1.0 + 0.05 × (handling_score − 3), 0.90, 1.20)`. |

### P50

```text
p50 = round(base_groom_minutes × size_mult × matting_mult × interval_mult × handling_mult)
```

### P90 (spread)

```text
spread_frac = 0.20 + 0.05 × (matting_risk − 1)     # 0.20 … 0.40
if overdue is known and overdue > 1:
  spread_frac += 0.10 × min(overdue − 1, 1.0)      # up to +0.10

p90 = max(p50, round(p50 × (1 + spread_frac)))
```

Higher matting risk and being overdue raise the level and/or widen the gap, by design.

### Worked example

Inputs: base `100`, matting `4`, size `l`, days `90`, interval `60`, handling `4`.

| Step | Value |
|------|-------|
| size_mult | 1.15 |
| matting_mult | 1.30 |
| overdue | 1.5 |
| interval_mult | 1.20 |
| handling_mult | 1.05 |
| **p50** | **188** |
| spread_frac | 0.40 |
| **p90** | **263** |

Locked by `tests/test_prior.py::test_walkthrough_example`.

## Calibration — predicted vs actual (#25)

Once visits store both `actual_minutes` and `predicted_min_*`, check whether the rules are systematically wrong (e.g. underestimating a breed).

**Script (not a DB view):** [`ops/sql/calibration_error.sql`](../ops/sql/calibration_error.sql) — see also [`ops/README.md`](../ops/README.md). Open in the Postgres extension or:

```powershell
Get-Content .\ops\sql\calibration_error.sql -Raw |
  docker compose exec -T db psql -U muttmetrics -d muttmetrics
```

| Output | How to read it |
|--------|----------------|
| `avg_error_p50` | `actual − p50`. **Positive** → under-predicted (jobs ran long). **Negative** → over-predicted |
| `p90_hit_rate` | Share of visits with `actual ≤ p90`. With enough rows, aim roughly near **0.9** |
| `n` | Sample size — ignore strong conclusions when `n` is tiny |

Three result sets: by **breed**, by **condition_score**, **overall**. Only completed (or legacy `status` NULL) visits that have predictions. Empty results are normal until dogs with breeds are saved via `POST /visits` after #24.

No dashboard; run when you want a weekly honesty check. Counts that reveal salon volume stay private (same idea as compliance notes).

## Future direction (not v0)

Breed is a **convenient cold-start package**, not the long-term load-bearing feature. Mixes and salon practice suggest duration is driven more by **coat + size + temperament/handling**, plus visit context (interval, condition, service).

Fitted / later priors must be able to produce P50/P90 **without requiring `breed_id`**. Tracked under M7: [#121](https://github.com/BOYSABIO/muttmetrics/issues/121) (feature matrix [#33](https://github.com/BOYSABIO/muttmetrics/issues/33), bakeoff [#34](https://github.com/BOYSABIO/muttmetrics/issues/34)).

## How we fill data (roadmap lock — #127)

Visit capture stays **thin** on purpose. Dog/owner detail is **enrichment**, not mid-groom homework.

| Track | Who | What |
|-------|-----|------|
| **Visit form (SPA)** | Groomer | Name → minutes → service → money → optional condition/photos. No CRM fields. |
| **Enrichment (SQL today)** | Maintainer | Breed/coat/size/handling, fixes — [`enrichment.md`](runbooks/enrichment.md) |
| **Maintainer browse/edit UI** | Maintainer | When SQL friction hurts — [#117](https://github.com/BOYSABIO/muttmetrics/issues/117) (not M9 client pages; not the groomer’s phone) |
| **Derived recompute** | System | `visit_count`, `last_visit_date`, … — **after** there are rows worth recomputing |
| **Coat-first predictions** | Later (M7) | Do not require breed — [#121](https://github.com/BOYSABIO/muttmetrics/issues/121) |

```text
condition polarity (#123) → visit habit (#22)
  → enrich when needed (#117 if SQL hurts)
  → M5 analytics on sparse-but-clear data
  → recompute / fitted model later
```

Empty nullable columns are fine. Ambiguous scales are not. Do not turn the phone visit form into a dog/owner CRM without a separate product decision.

## Out of scope (here)

- Fitting coefficients from salon data / auto-tuning the formula
- Service-slug adjustments inside the prior (nails vs full groom) — `service_id` on the preview is validated only for now
- Day packer
- Postgres `CREATE VIEW` for calibration (a committed script is enough for maintainer runs)

## Related

- [ADR-001](architecture/adr/001-derived-fields.md) — `days_since_last` and predictions are system-computed on the visit, not hand-edited
- Breed cold-start values — `src/muttmetrics/seed/data.py` (`base_groom_minutes`, `matting_risk`, `recommended_interval_days`)
- Coat/size/temperament-first predictions — [#121](https://github.com/BOYSABIO/muttmetrics/issues/121)
- Thin capture vs enrichment sequencing — [#127](https://github.com/BOYSABIO/muttmetrics/issues/127), maintainer UI [#117](https://github.com/BOYSABIO/muttmetrics/issues/117)
