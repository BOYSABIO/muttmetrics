# Rules-based duration prior (P50 / P90)

Hand-encoded baseline for how long a groom will take, **before** any fitted model. Implemented as a pure function in [`src/muttmetrics/prior.py`](../src/muttmetrics/prior.py) ([#23](https://github.com/BOYSABIO/muttmetrics/issues/23)).

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
- **On visit create** — `POST /visits` computes `days_since_last` and stores `predicted_min_p50` / `predicted_min_p90` when breed priors exist ([#24](https://github.com/BOYSABIO/muttmetrics/issues/24)); see `api/services/visit_predictions.py`. A lookup CLI/endpoint is [#26](https://github.com/BOYSABIO/muttmetrics/issues/26).

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

## Out of scope (this doc / #23)

- Fitting coefficients from salon data
- Service-slug adjustments (nails vs full groom) — can layer later
- Persisting onto `visit.predicted_min_*`
- Day packer

## Related

- [ADR-001](architecture/adr/001-derived-fields.md) — `days_since_last` and predictions are system-computed on the visit, not hand-edited
- Breed cold-start values — `src/muttmetrics/seed/data.py` (`base_groom_minutes`, `matting_risk`, `recommended_interval_days`)
