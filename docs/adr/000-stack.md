# Architecture Decision Record

## ADR-000: Stack — Python, Postgres, SQLAlchemy, Alembic, FastAPI

- **Status:** Accepted
- **Date:** 2026-08-25
- **Context:** MuttMetrics is a learning project that also has to hold real business data. The primary near-term work is schema, import, capture, and statistical/ML priors — not a marketing site.

### Decision

| Layer | Choice |
|-------|--------|
| Language | Python 3.11+ |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic |
| API (when needed) | FastAPI |
| Hosted DB (target) | Neon (or equivalent) — documented in M1 |
| Frontend | Staged: **A** FastAPI HTML/Jinja capture (#63) → **B** Vite+React+TS capture SPA (#69) → **C** Next for owner-facing (#41, M9). Python API stays the source of truth. |

### Consequences

- One Python environment for API, ETL, notebooks, and models.
- Schema changes always go through Alembic — no hand-edited prod SQL as source of truth.
- Prisma / Node ORM is explicitly out of scope for the core service.
- Capture UI may move from HTML to React without a backend rewrite; Next is for owner/multi-page surfaces, not a requirement for the first visit form.

### Alternatives considered

- **Prisma + TypeScript end-to-end:** better if the product were UI-first; weaker for data-science muscle and notebooks.
- **Django:** batteries-included admin is tempting for capture, but heavier than needed; FastAPI + a thin form keeps the learning surface smaller.
