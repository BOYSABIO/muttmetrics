# MuttMetrics capture UI (React)

Vite + React + TypeScript SPA for groomer visit capture ([#69](https://github.com/BOYSABIO/muttmetrics/issues/69)–[#72](https://github.com/BOYSABIO/muttmetrics/issues/72)). This is the **only** groomer capture UI — it calls the same FastAPI JSON routes as OpenAPI `/docs` (`GET /pets`, `POST /owners`, `POST /pets`, `POST /visits`). The old Jinja `/capture` form was removed in [#86](https://github.com/BOYSABIO/muttmetrics/issues/86).

Setup and run instructions: [../README.md](../README.md) and [../CONTRIBUTING.md](../CONTRIBUTING.md). Production (home server, Tailscale): [../docs/runbooks/home-server.md](../docs/runbooks/home-server.md); the groomer's side: [../docs/runbooks/groomer-access.md](../docs/runbooks/groomer-access.md).

**E2E smoke (#196):** `e2e/*.spec.ts` + `npm run e2e` (needs API + Syn* demo DB). Full steps: [CONTRIBUTING → End-to-end smoke](../CONTRIBUTING.md#end-to-end-smoke-196).
