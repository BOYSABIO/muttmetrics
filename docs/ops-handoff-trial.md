# Trial handoff runbook — phone capture trial

Operational procedure for [#82](https://github.com/BOYSABIO/muttmetrics/issues/82). Follow it top to bottom, check each step before moving on.

Transport is **Tailscale**, not plain salon Wi-Fi. Everything else in #82 is unchanged.

**Roles in this doc:** **User** = the groomer capturing visits on a phone. **Owner** = the maintainer who runs the stack and reads the database.

Related: [ops-db-peek.md](./ops-db-peek.md) (looking at rows), [ops-enrichment.md](./ops-enrichment.md) (fixing rows afterwards), [CONTRIBUTING](../CONTRIBUTING.md) (normal dev setup).

---



## 0. What is where

```text
User phone (Tailscale app)
      │  http://10.x.x.x:5174
      ▼
tailnet ──► subnet router ──► VLANX ──►    PC
                                            │
                                   vite preview :5174   (static files in frontend/dist + /api proxy)
                                            │  proxies /api/* → 127.0.0.1:8000
                                   FastAPI  127.0.0.1:8000
                                            │
                                   Postgres 127.0.0.1:5432 (Docker)
```

**Only port 5174 is reachable from the tailnet.** The API and the database listen on `127.0.0.1` only — they are reachable by programs on the PC, nobody else. The phone never talks to FastAPI directly; the preview server does that on the PC's behalf.


| Thing                  | Value                                                      |
| ---------------------- | ---------------------------------------------------------- |
| PC address on VLANX    | `10.x.x.x` (DHCP — see troubleshooting if it ever changes) |
| URL User opens         | `http://10.x.x.x:5174`                                     |
| Tailscale grant        | `group:<groomer-group>` → `10.x.x.x` → `tcp:5174` only        |
| Tailscale policy tests | assert 5174 allowed, 8000 / 5432 / gateway denied          |


Prerequisites, once per person: User has the Tailscale app installed, is signed in, is a **Member** (not Admin), and is in `group:<groomer-group>`.

---



## 1. Start the stack (in this order)

Order matters: the API needs the database, the frontend needs the API.

### 1.1 Database

Docker Desktop must be running.

```bash
docker compose up -d
docker compose ps
```

**Check:** `STATUS` is `Up ... (healthy)` and `PORTS` shows exactly `127.0.0.1:5432->5432/tcp`.
If it shows `0.0.0.0:5432`, the `docker-compose.yml` change was reverted — fix before continuing.

### 1.2 API — trial mode, no reload

```bash
uvicorn muttmetrics.api.app:app --host 127.0.0.1 --port 8000
```

Not `python -m muttmetrics.api` — that entry point enables `--reload`, which restarts the API whenever a file under `src/` changes. During a trial that can restart the server in the middle of User's save.

**Check:**

```bash
curl.exe -s http://127.0.0.1:8000/health
```



### 1.3 Frontend — build, then preview

```bash
cd frontend
npm run build
npm run preview
```

**Check:** preview prints a **Local** URL on 5174 and a **Network** URL containing `http://10.x.x.x:5174/`. No Network URL → see troubleshooting.

`npm run build` bakes `frontend/.env` (`VITE_API_KEY`) into `frontend/dist/`. If that key changes, rebuild.

### 1.4 Your own smoke test — before User touches it

1. On the PC: open `http://localhost:5174`, search a known dog. Rows come back → the proxy and API work.
2. On your phone over Tailscale: open `http://10.x.x.x:5174`, search the same dog. Rows come back → the network path works.

Do not skip step 2. It is the only check that proves Tailscale, the grant, and the preview binding all line up.

---



## 2. Pre-flight before a real session

- [ ] **No stray servers.** A forgotten dev server holding a port makes preview fail to start:

  ```powershell
  Get-NetTCPConnection -LocalPort 5173,5174,8000 -State Listen | Select-Object LocalPort, LocalAddress, OwningProcess
  Get-Process -Id <OwningProcess>
  ```

- [ ] **PC will not sleep.** If the PC sleeps mid-groom, User's page dies. Set the power plan to never sleep for the session, and put it back afterwards.
- [ ] **Baseline row count**, so you can tell afterwards exactly what was added:

  ```bash
  docker compose exec db psql -U muttmetrics -d muttmetrics -c "SELECT count(*) FROM visit;"
  ```

- [ ] **Backup** if there is already real data (see §6).
- [ ] **Working tree committed**, so an accidental edit is easy to undo.

---



## 3. User's phone checklist

Send this part to User; it is all they need.

1. **Open** `http://10.x.x.x:5174` (Tailscale must be on). Add it to the home screen for next time.
2. **Find the dog:** type part of the name → **Search** → tap the right row (the owner name is shown next to it).
3. **New client** (first visit only): tap **New client** → owner name → dog name → continue. Breed and the rest get filled in later by Owner; do not worry about them.
4. **Step 1 — photo:** skip it. Leave the field empty and continue.
5. **Step 2 — timer:** press **Start** when you start the groom, **Stop** when you finish. If you forget, type the minutes in by hand. Minutes is the one number that matters.
6. **Step 3 — details:** the date is already today. Condition score and "what surprised me" are optional but useful. Tap **Save visit** **once** and wait for the green confirmation with a visit number.
7. **If anything fails:** write the dog name and the minutes on paper and tell Owner. Nothing is lost — it can be added later.

**Must fill:** the dog (found or newly created) and the minutes. **Everything else can be skipped.**

Known rough edges, do not fix mid-trial: tapping **Save** twice may create two visits; if the phone reloads the page mid-groom the timer is lost ([#88](https://github.com/BOYSABIO/muttmetrics/issues/88)).

---



## 4. Rules while a session is live

The preview server freezes the **frontend** only. The API and the database are shared with whatever you do on the PC.


| Don't                            | Why                                                              |
| -------------------------------- | ---------------------------------------------------------------- |
| `npm run build`                  | Empties `dist/` for a moment; a request during that window fails |
| Edit files under `src/`          | Even without `--reload`, a restart kills in-flight requests      |
| `alembic upgrade` / `downgrade`  | Changes his database underneath him                              |
| `pytest`                         | Local tests write into this same database                        |
| `docker compose down`            | Stops the database mid-groom                                     |
| Save test visits from dev (5173) | They land in the same tables as his real ones                    |


If you must change something, wait for a green "Saved visit_id=…" on his phone first.

---



## 5. After the session — confirm the rows landed

```sql
-- how many, versus the baseline from §2
SELECT count(*) FROM visit;

-- today's visits, readable
SELECT v.visit_id, d.name AS dog, o.name AS owner, v.visit_date, v.actual_minutes,
       v.condition_score, v.what_surprised_me
FROM visit v
JOIN dog d   ON d.dog_id = v.dog_id
JOIN owner o ON o.owner_id = v.owner_id
WHERE v.visit_date = CURRENT_DATE
ORDER BY v.visit_id;

-- double-tap check: same dog twice on the same day
SELECT dog_id, visit_date, count(*)
FROM visit
WHERE visit_date = CURRENT_DATE
GROUP BY dog_id, visit_date
HAVING count(*) > 1;
```

Connection details and the editor setup are in [ops-db-peek.md](./ops-db-peek.md).

Then:

- **Count check:** rows added == grooms done? If not, find out which one is missing and why — that is the most valuable finding of the whole trial.
- **Enrich afterwards**, never during: breed, owner contact, corrections → [ops-enrichment.md](./ops-enrichment.md).
- **Friction notes** → a comment on [#82](https://github.com/BOYSABIO/muttmetrics/issues/82): what was skipped, what was asked about, what annoyed, where there was hesitation. Notes only, no fixes mid-trial.
- **Go / no-go** for the always-on deploy ([#83](https://github.com/BOYSABIO/muttmetrics/issues/83)) recorded as a comment.

---



## 6. Data safety

The data is the point of the project. A UI that is down for an hour costs nothing; a lost or duplicated visit row corrupts the very dataset M4 depends on.

**Backup before anything schema-related** (`alembic upgrade`, a new migration, an experiment):

```bash
docker compose exec db pg_dump -U muttmetrics -d muttmetrics -f /tmp/backup.sql
docker compose cp db:/tmp/backup.sql ./backup-YYYY-MM-DD.sql
```

Dump to a file inside the container and copy it out — a PowerShell `>` redirect writes UTF-16 and produces a dump that will not restore. Backups are gitignored; never commit one.


| Never                                      | Because                                                                                                           |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| `docker compose down -v`                   | Deletes the volume — every visit ever captured                                                                    |
| Apply an autogenerated migration unread    | A rename becomes drop + add; the column's data is gone ([#89](https://github.com/BOYSABIO/muttmetrics/issues/89)) |
| `alembic downgrade` on a DB with real rows | `downgrade()` drops tables and columns                                                                            |


`docker compose stop` and `docker compose down` (no `-v`) are safe: the volume survives.

---



## 7. Shut down

```bash
# frontend terminal
Ctrl+C
# API terminal
Ctrl+C
docker compose stop
```

Restore the PC's sleep settings.

---



## 8. Troubleshooting


| Symptom                                            | Likely cause                                                                         | Fix                                                                                                                                             |
| -------------------------------------------------- | ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Phone: page never loads                            | Tailscale off on his phone, or PC asleep                                             | Check the Tailscale app; wake the PC                                                                                                            |
| Phone: page never loads, PC fine                   | Grant or IP mismatch                                                                 | Tailscale admin → the rule must be the PC's address on `tcp:5174`; confirm the PC still has that address                                                   |
| Phone: loads, search hangs forever                 | API not running                                                                      | Check terminal 2; `curl.exe -s http://127.0.0.1:8000/health`                                                                                    |
| `Error: Port 5174 is already in use`               | Preview already running, or a stray process                                          | `Get-NetTCPConnection -LocalPort 5174 -State Listen`, then `Get-Process -Id <pid>`; `strictPort` is doing its job                               |
| Preview prints no Network URL                      | `preview.host` not `0.0.0.0` in `vite.config.ts`, or Windows Firewall blocked `node` | Check the config; allow node on Private networks                                                                                                |
| `Can't reach server` / `Server error (5xx)` / `Not saved — try again` | API down, or server returned an error (often DB) | Check terminal 2 / `curl.exe -s http://127.0.0.1:8000/health`; search or save again. Browser console has the detailed `console.error`. |
| First DB query takes ~a minute                     | `localhost` resolving to IPv6 `::1` while Postgres listens on IPv4 only              | Use `127.0.0.1` in `.env` and in the Vite proxy target                                                                                          |
| User's changes don't appear                   | He is running the old bundle                                                         | He reloads the page; you rebuild if the code changed                                                                                            |
| PC address changed                     | DHCP lease moved                                                                     | Add a static mapping in OPNsense; update the Tailscale rule                                                                                     |


---



## 9. What this trial decides

It is a product test, not an infrastructure test. One question: **does User open it and save a visit without Owner typing for them?**

- **Yes** → keep using this desktop + Tailscale runbook for now (Spencer manages on/off). Always-on OptiPlex ([#93](https://github.com/BOYSABIO/muttmetrics/issues/93)) and cloud ([#83](https://github.com/BOYSABIO/muttmetrics/issues/83)) stay iceboxed until the shop box can live in the salon.
- **No** → the friction notes say why, and that gets fixed before spending anything on hosting.

