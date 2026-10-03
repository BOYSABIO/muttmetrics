# Ops: weekly capture compliance

How the maintainer measures **% of real grooms that left a visit row** (#22).

This is a **manual product metric**, not a dashboard. The groomer is asked for the denominator; SQL gives the numerator. Do it once per salon week (Mon–Sun) for the first month of formal capture.

Schema / peek: [`db-peek.md`](./db-peek.md). Numerator SQL: [`scripts/SQL/compliance_week.sql`](../../scripts/SQL/compliance_week.sql).

## Definition

| Piece | Meaning |
|-------|---------|
| **Week** | Monday–Sunday on `visit.visit_date` (salon calendar) |
| **Numerator** | Completed visits in that week (`status` is `completed` or `NULL`; exclude `cancelled` / `no_show`) |
| **Denominator** | How many dogs were groomed that week (ask the groomer; not booking software) |
| **Compliance %** | `100 × numerator ÷ denominator` — skip if denominator is 0 |

Formal measurement starts **2026-10-06** (see #22). Earlier rows can exist; they are not the start of this ritual.

## Privacy (public repo)

This runbook and the SQL are **public** (how to measure). Weekly **counts and %** are **business volume** — same category as backup-drill row counts ([`backup.md`](./backup.md) § drills).

| Put here (git / public #22) | Put in `docs/notes/` (gitignored) |
|-----------------------------|-----------------------------------|
| Procedure, definition, SQL path | `grooms_reported`, `completed_visits`, compliance % |
| Qualitative notes with no volume (“habit still weak”) | Client / dog names, dates tied to counts |

Do **not** paste weekly numbers into a public issue comment. Record them locally (below). A public #22 comment may only say the week was closed and logged privately, or a qualitative note with no counts.

## Weekly procedure

1. **Pick the week** — last completed Mon–Sun (or the week you are closing). Example: `2026-10-06` … `2026-10-12`.
2. **Edit dates** in [`scripts/SQL/compliance_week.sql`](../../scripts/SQL/compliance_week.sql) (both queries).
3. **Run the script** (Postgres extension, or from repo root):

   ```powershell
   Get-Content .\scripts\SQL\compliance_week.sql -Raw |
     docker compose exec -T db psql -U muttmetrics -d muttmetrics
   ```

4. **Read the count** (`completed_visits`) and skim the list — wrong dates or doubles show up there.
5. **Ask the groomer** — how many dogs that Mon–Sun. Do not invent the number from bookings.
6. **Compute** — `compliance % = 100 * completed_visits / grooms_reported` (whole % is fine).
7. **Record privately** — append to `docs/notes/compliance-weeks.md` (gitignored; create if missing) using the template below. Optional: on #22, note only that the week was logged (no numbers).

## Record format (private)

Append one block per week to `docs/notes/compliance-weeks.md`:

```text
### Compliance week YYYY-MM-DD → YYYY-MM-DD

- grooms_reported (ask): N
- completed_visits (SQL): N
- compliance %: N%
- notes: (optional — e.g. photos often; visit form skipped after pay)
```

## Interpreting the number

| Range (rough) | What it suggests |
|---------------|------------------|
| High and stable | Capture habit is real; safer to invest in M4 priors |
| Mid / noisy | Friction or forgetfulness — fix habit/process before analytics |
| Near zero with real grooms | Capture not adopted — stop and address motivation / ritual, not more features |

Do **not** use this % to grade individual dogs or clients. It only answers: “are we writing rows when grooms happen?”

## Out of scope (v0)

- Booking calendar vs visits (later, if needed)
- Automated denominator
- Dashboard or API endpoint for this metric
- Publishing weekly counts on public GitHub issues
