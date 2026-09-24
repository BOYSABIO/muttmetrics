# MuttMetrics capture UI (React)

Vite + React + TypeScript SPA for groomer visit capture ([#69](https://github.com/BOYSABIO/muttmetrics/issues/69)–[#72](https://github.com/BOYSABIO/muttmetrics/issues/72)). This is the **only** groomer capture UI — it calls the same FastAPI JSON routes as OpenAPI `/docs` (`GET /dogs`, `POST /owners`, `POST /dogs`, `POST /visits`). The old Jinja `/capture` form was removed in [#86](https://github.com/BOYSABIO/muttmetrics/issues/86).

Setup and run instructions: [../README.md](../README.md) and [../CONTRIBUTING.md](../CONTRIBUTING.md). Phone trial over Tailscale: [../docs/ops-handoff-trial.md](../docs/ops-handoff-trial.md).
