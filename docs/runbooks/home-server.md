# Runbook: the home server, rebuilding it and running it

The always-on box the groomer's phone talks to ([#93](https://github.com/BOYSABIO/muttmetrics/issues/93)). Part A rebuilds it from a blank disk, with a check after every step; Part B is the day-to-day; Part C is what to do when it misbehaves.

Config files: [`ops/server/`](../../ops/server/README.md), copied rather than retyped. Related: [`release.md`](./release.md) (releases and deploys), [`backup.md`](./backup.md), [`groomer-access.md`](./groomer-access.md) (the groomer's side), [`privacy.md`](../architecture/privacy.md) (where the data lives).

**Placeholders:** `<admin>` (the admin account), `<workstation-ip>` (the maintainer's PC on the LAN), `<tailnet>` (the tailnet's DNS name, `tailXXXX.ts.net`), `<groomer-group>` (the groomer's Tailscale group). The real values are in the maintainer's private notes, never in this repo.

---

## What runs where

```text
groomer's phone ──Tailscale (mobile data)──► muttmetrics node (the box's own Tailscale)
                                               │ tailscale serve: HTTPS 443, tailnet only
                                               ▼
                                       Caddy 127.0.0.1:8080 ── /api/* + X-API-Key ──► API 127.0.0.1:8000
                                               │ static: /opt/muttmetrics/frontend/dist           │
                                                                                Postgres (Docker) 127.0.0.1:5432
maintainer ──SSH, key only──► <admin>@box   (by name over Tailscale; or from <workstation-ip> on the LAN)
```

| Thing | Value |
|---|---|
| OS | Debian 13, minimal; LVM; no full-disk encryption (the box must reboot unattended) |
| Accounts | `<admin>`: SSH key + sudo. `muttmetrics`: the app account (owns code and data, runs the services and deploys; groups `docker` only; password locked; no SSH) |
| Code | `/opt/muttmetrics`: a release **tag** checked out (detached), `.venv/`, `.env` (600) |
| Data | `/srv/muttmetrics/photos`, `/srv/muttmetrics/backups` (700; files 600) |
| Listening | LAN: SSH only. Tailscale: 443 (`serve`). Localhost: 8080 (Caddy), 8000 (API), 5432 (Postgres), 2019 (Caddy admin) |
| URL | `https://muttmetrics.<tailnet>` (full name; the certificate doesn't cover the short name) |
| Timers | `muttmetrics-backup` (00:30, reports to Healthchecks), `muttmetrics-heartbeat` (every 5 min), unattended-upgrades (reboot 04:30 when needed) |
| Watching | Healthchecks.io (free; outgoing pings only, no client data) → Telegram. Ping URLs only in `/etc/muttmetrics/healthchecks.env` (root, 600) |

---

## Part A: rebuild from scratch

Each step ends in a **check**. Don't start the next step until it passes.

### A1. Box basics (as the install user, then `<admin>`)

```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y unattended-upgrades apt-listchanges curl git ca-certificates nftables tcpdump
sudo dpkg-reconfigure -plow unattended-upgrades                  # answer Yes (= ops/server/apt/20auto-upgrades)
sudo install -m 644 52muttmetrics-reboot /etc/apt/apt.conf.d/    # from ops/server/apt/ (copy it over, or paste it)
sudo timedatectl set-timezone Europe/Berlin
```

**Check:** `cat /etc/apt/apt.conf.d/20auto-upgrades` shows both lines ending in `"1"`; `timedatectl` shows `Europe/Berlin` and `System clock synchronized: yes`.

**Fixed address:** a DHCP reservation for the box's MAC (`ip link show <nic>`) in the infrastructure range, matched on the **MAC only** (no client ID). Reboot to pick it up. **Check:** `ip -br addr` shows the reserved address.

**Admin account and keys:**

```bash
sudo adduser <admin>
sudo usermod -aG sudo,adm,systemd-journal <admin>
```

On each device the maintainer uses (one key per device, so a lost laptop is one line to delete):

```powershell
ssh-keygen -t ed25519 -C "<device>-to-muttmetrics"     # with a passphrase
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh <admin>@<box-ip> "umask 077; mkdir -p ~/.ssh; cat >> ~/.ssh/authorized_keys"
```

A device that can't reach the box yet: copy its **`.pub`** file over by any means and append it from a working session.

**Check:** a new window logs in with only the key's passphrase.

**SSH hardening:** copy `ops/server/ssh/10-muttmetrics-hardening.conf` to `/etc/ssh/sshd_config.d/`, replace `<admin>`, then:

```bash
sudo sshd -t && sudo sshd -T | grep -Ei '^(passwordauthentication|permitrootlogin|allowusers) '
sudo systemctl reload ssh
```

**Check (from a new window; keep the old one open until this passes):** key login works; `ssh -o PubkeyAuthentication=no <admin>@…` and `ssh muttmetrics@…` both get `Permission denied (publickey)`.

### A2. Tailscale

**In the admin console first:**

- **Tailnet name:** under DNS, check it's one you don't mind being public. Every HTTPS certificate puts it in public Certificate Transparency logs permanently.
- **Tag:** create `tag:muttmetrics`, owner `autogroup:admin`.
- **Grant:** `group:<groomer-group>` → `tag:muttmetrics`, `tcp:443`, nothing else.
- **Test,** typed from the requirement (**not** copied from the rule): accept `tag:muttmetrics:443`; deny `tag:muttmetrics:22`, `:8000`, `:5432`.
- **The groomer's phone:** disable key expiry on it.

The tag, grant and test are in [`ops/server/tailscale/policy-snippet.hujson`](../../ops/server/tailscale/policy-snippet.hujson), ready to merge into the policy file.

```bash
curl -fsSL https://pkgs.tailscale.com/stable/debian/trixie.noarmor.gpg | sudo tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null
curl -fsSL https://pkgs.tailscale.com/stable/debian/trixie.tailscale-keyring.list | sudo tee /etc/apt/sources.list.d/tailscale.list
sudo apt update && sudo apt install -y tailscale
sudo tailscale up --hostname=muttmetrics --advertise-tags=tag:muttmetrics --accept-dns=false
sudo tailscale set --auto-update
```

**Check:**

- the console shows `muttmetrics` with the tag and **Expiry disabled** (tagged devices get that automatically);
- `ssh <admin>@muttmetrics` works by name, and `echo $SSH_CONNECTION` on the box starts with the device's `100.x` address (not a router's LAN address).

### A2b. Host firewall

Copy `ops/server/nftables/nftables.conf` to `/etc/nftables.conf` and set `WORKSTATION` to `<workstation-ip>`. Then apply it **with an automatic undo** in case it locks you out:

```bash
sudo nft -c -f /etc/nftables.conf && echo "syntax OK"
sudo systemd-run --unit=fw-rollback --on-active=5m /usr/sbin/nft delete table inet host_fw
sudo nft -f /etc/nftables.conf
```

**Check, within 5 minutes:**

- `ssh <admin>@muttmetrics` works (Tailscale);
- `ssh -o ConnectTimeout=5 <admin>@<box-ip>` from a device going through a subnet router **times out**, and `sudo journalctl -k | grep "host_fw drop"` shows it;
- with the workstation's Tailscale **off**, it reaches the box directly on the LAN.

Then:

```bash
sudo systemctl stop fw-rollback.timer
sudo systemctl enable nftables
sudo reboot
```

**Check after the reboot:** `sudo nft list tables` shows `inet host_fw` next to Tailscale's tables.

### A3. Runtime

**Docker** (from Docker's repo):

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo install -m 644 daemon.json /etc/docker/daemon.json          # ops/server/docker/
sudo systemctl restart docker
```

**Check:** `sudo docker info | grep -E "Logging Driver|Live Restore"` shows `local` and `true`; `sudo nft list tables` still lists `inet host_fw`.

**Python and Node 22** (Node is only used to build the SPA during a deploy):

```bash
sudo apt install -y python3-venv
curl -fsSL https://deb.nodesource.com/setup_22.x -o /tmp/nodesource_setup.sh && sudo bash /tmp/nodesource_setup.sh
sudo apt install -y nodejs
```

**Check:** `node -v` prints `v22.x` and `apt-cache policy nodejs` shows `nodesource`.

**The app account, folders, code and `.env`:**

```bash
sudo deluser muttmetrics sudo 2>/dev/null; sudo passwd -l muttmetrics     # if the installer created it as an admin
sudo usermod -G docker muttmetrics                                       # docker only (root-equivalent: nobody else)
sudo install -d -o muttmetrics -g muttmetrics -m 755 /opt/muttmetrics
sudo install -d -o muttmetrics -g muttmetrics -m 700 /srv/muttmetrics /srv/muttmetrics/photos /srv/muttmetrics/backups

sudo -iu muttmetrics
git clone https://github.com/BOYSABIO/muttmetrics.git /opt/muttmetrics
cd /opt/muttmetrics && git checkout --detach vX.Y.Z && python3 -m venv .venv
umask 077
API_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
PG=$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')
cat > .env <<EOF
API_KEY=$API_KEY
POSTGRES_PASSWORD=$PG
DATABASE_URL=postgresql+psycopg://muttmetrics:$PG@127.0.0.1:5432/muttmetrics
PHOTO_ROOT=/srv/muttmetrics/photos
BACKUP_ROOT=/srv/muttmetrics/backups
EOF
unset API_KEY PG
docker compose up -d
.venv/bin/pip install --quiet -e . && .venv/bin/alembic upgrade head
exit
```

**Check:**

- `sudo ls -l /opt/muttmetrics/.env` shows `-rw------- muttmetrics`;
- `docker compose ps` shows `(healthy)`;
- `sudo ss -tlnp | grep 5432` shows `127.0.0.1` only.

**The API service:** install `ops/server/systemd/muttmetrics-api.service`, then:

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now muttmetrics-api
curl -s http://127.0.0.1:8000/health; echo
```

**Check:** `/health` is OK. Then `sudo systemctl kill muttmetrics-api`, and 5 s later `systemctl show -p NRestarts muttmetrics-api` is ≥ 1 and `/health` answers again. `systemctl show -p UMask muttmetrics-api` is `0077`: photos it writes are owner-only (`600`), and so are their backup copies.

**Caddy:**

```bash
sudo apt install -y caddy && sudo systemctl stop caddy           # the package starts a welcome page on :80
sudo install -D -m 644 caddy-muttmetrics.conf /etc/systemd/system/caddy.service.d/muttmetrics.conf
sudo install -m 644 Caddyfile /etc/caddy/Caddyfile               # both from ops/server/caddy/
sudo systemctl daemon-reload
sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl start caddy
sudo -iu muttmetrics sh -c 'cd /opt/muttmetrics/frontend && npm ci && npm run build'
```

**Check:**

- `curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/api/services` returns **200** (Caddy adds the key);
- the same against `:8000/services` returns **401**;
- `ss -tlnp` shows nothing on `:80`.

**HTTPS:** enable HTTPS certificates when asked, and leave **Funnel off**: it would publish to the internet and let every member do the same.

```bash
sudo tailscale serve --bg --https=443 http://127.0.0.1:8080
tailscale serve status        # "(tailnet only)"
```

**Check:** `curl.exe -s https://muttmetrics.<tailnet>/api/health` from the maintainer's PC returns OK.

**Deploy permissions:** install `ops/server/sudoers/muttmetrics-deploy` (mode **440**, then `sudo visudo -cf …`) and append `ops/server/profile/deploy-env.sh` to `/home/muttmetrics/.profile`.

**Check:** as `muttmetrics`:

- `sudo -n systemctl restart muttmetrics-api caddy` works;
- `sudo -n systemctl restart ssh` asks for a password.

### A4. First deploy

As `muttmetrics` in `/opt/muttmetrics`:

```bash
git status --short                                   # must be empty
.venv/bin/python ops/deploy.py --to vX.Y.Z
```

**Check:** it ends in **`Deploy OK.`**, and the footer on a phone over Tailscale shows `vX.Y.Z`.

### A5. Backups

Install `ops/server/systemd/muttmetrics-backup.{service,timer}`, then:

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now muttmetrics-backup.timer
sudo systemctl start muttmetrics-backup.service
journalctl -u muttmetrics-backup -n 8 --no-pager     # ends in "OK"
```

Then run a **restore drill** ([`backup.md`](./backup.md) §5) and log it privately. The encrypted second copy on another device is [#221](https://github.com/BOYSABIO/muttmetrics/issues/221) (after M6; an accepted risk until then).

### A5b. Monitoring (Healthchecks.io, #104)

The box can't report its own death, so an outside service watches for **missing** signals. The box only makes outgoing HTTPS requests: no port opens, and no client data is sent (each ping is empty).

1. **On Healthchecks.io** (free plan), create a project with two checks, and connect Telegram (or Discord) under *Integrations*. Email is added by default; turn it off per check if one push channel is enough:
   - `muttmetrics-heartbeat`: Simple, period **5 min**, grace **25 min**;
   - `muttmetrics-backup`: Cron `30 0 * * *`, time zone `Europe/Berlin`, grace **1 hour**.
2. **The ping URLs are secrets** (anyone who has one can fake "all is well"). Put them only on the box:
   ```bash
   sudo install -d -m 755 /etc/muttmetrics
   sudo install -m 600 /dev/null /etc/muttmetrics/healthchecks.env
   sudoedit /etc/muttmetrics/healthchecks.env          # format: ops/server/monitoring/healthchecks.env.example
   ```
3. **Install** `muttmetrics-heartbeat.{service,timer}` from `ops/server/systemd/` (the backup unit from A5 already reports once the env file exists: its `EnvironmentFile=-…` is optional, so A5 works before A5b), then:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now muttmetrics-heartbeat.timer
   sudo systemctl start muttmetrics-heartbeat.service muttmetrics-backup.service
   ```

**What each check covers:**

| Check | The box sends | Alarm when |
|---|---|---|
| Heartbeat | every 5 min: a ping if `/api/services` answers through Caddy (Caddy + API + key + Postgres), `/fail` if not | the app is broken (`/fail`, immediately); **or nothing for ~30 min**: power, internet, a frozen box, the USB SSD |
| Backup | after every run: a ping on success, `/fail` on any failure (`ExecStopPost`) | the backup failed (immediately); **or it didn't run** (no success by ~01:30) |

**Check:** both checks turn green in the Healthchecks dashboard. Stop the API (`sudo systemctl stop muttmetrics-api`), run `sudo systemctl start muttmetrics-heartbeat.service`, and a 🔴 message arrives; start the API again and run the heartbeat once more: ✅.

**Reboot check:** `sudo reboot`, then `systemctl is-active docker muttmetrics-api caddy nftables tailscaled` shows five `active`, and `/health` answers over HTTPS.

### A6. Moving data in (from another host)

Do it after hours, with no pending draft on the groomer's phone:

1. **On the old host:** stop the API and the SPA server (nothing listening), run `python ops/backup.py`, and note the counts:
   ```sql
   select (select count(*) from owner)||' / '||(select count(*) from pet)||' / '||(select count(*) from visit)||' / '||(select count(*) from photo);
   ```
   The schema must be at the same Alembic head as the box.
2. **Copy across:** the dump and `PHOTO_ROOT` go into a **private** folder (`mkdir -m 700 ~/import`), not `/tmp`.
3. **On the box:**
   ```bash
   sudo systemctl stop muttmetrics-api
   sudo install -o muttmetrics -g muttmetrics -m 600 ~/import/db/muttmetrics-*.dump /srv/muttmetrics/backups/db/
   sudo -iu muttmetrics sh -c 'cd /opt/muttmetrics &&
     docker compose exec -T db dropdb -U muttmetrics muttmetrics &&
     docker compose exec -T db createdb -U muttmetrics muttmetrics &&
     docker compose exec -T db pg_restore -U muttmetrics -d muttmetrics < /srv/muttmetrics/backups/db/<final>.dump &&
     .venv/bin/alembic current'
   sudo cp -r ~/import/photos/. /srv/muttmetrics/photos/ && sudo chown -R muttmetrics:muttmetrics /srv/muttmetrics/photos
   sudo find /srv/muttmetrics/photos -type d -exec chmod 700 {} + ; sudo find /srv/muttmetrics/photos -type f -exec chmod 600 {} +
   sudo systemctl start muttmetrics-api
   sudo -iu muttmetrics sh -c 'cd /opt/muttmetrics && .venv/bin/python ops/photo_sweep.py'
   rm -rf ~/import
   ```
4. **Check:**
   - the counts match;
   - `alembic current` shows `(head)`;
   - `photo_sweep` finds no orphans;
   - delete any dumps the box took of its *empty* database, so nobody restores one by mistake;
   - take a backup, then run a restore drill.

---

## Part B: day to day

| Job | How |
|---|---|
| **Deploy / roll back** | As `muttmetrics` in `/opt/muttmetrics`: `.venv/bin/python ops/deploy.py --to vX.Y.Z` ([`release.md`](./release.md)). Never edit, `npm audit fix` or upgrade npm in the checkout; the deploy refuses a dirty tree |
| **Updates** | Debian packages (incl. Python and Caddy): automatic, reboot at 04:30 when needed. Tailscale: auto-update. **Docker and Node: monthly** `sudo apt update && sudo apt upgrade` |
| **Alerts** | Healthchecks.io → Telegram (§A5b). Email is turned off per check on purpose; switch it back on there if Telegram ever stops being reliable. Pausing a check during planned work (e.g. a long restore): *Pause* on its page, so it doesn't page you |
| **Is it healthy?** | `systemctl is-active docker muttmetrics-api caddy nftables tailscaled`; `systemctl --failed`; `curl -s http://127.0.0.1:8000/health` |
| **Backups OK?** | `systemctl list-timers muttmetrics-backup.timer`; `journalctl -u muttmetrics-backup -n 8`; `sudo -iu muttmetrics sh -c 'cd /opt/muttmetrics && .venv/bin/python ops/backup_check.py'` |
| **Logs** | API `journalctl -u muttmetrics-api`; Caddy `journalctl -u caddy`; Postgres `docker compose logs db` (as `muttmetrics`); firewall drops `journalctl -k \| grep host_fw`; tailnet rule drops `journalctl -u tailscaled \| grep Drop` |
| **Rotate the API key** | As `muttmetrics`: edit `API_KEY` in `.env`, then `sudo systemctl restart muttmetrics-api caddy`. No rebuild; the browser never had it |
| **Add a device's SSH key** | Append its `.pub` to `/home/<admin>/.ssh/authorized_keys` from a working session. Remove the line when the device is gone |
| **Look at real data** | On the box only (`docker compose exec db psql …` as `muttmetrics`), or through an SSH tunnel with a read-only role ([#33](https://github.com/BOYSABIO/muttmetrics/issues/33)). Never copy dumps to the dev PC |
| **A power cut** | Until [#217](https://github.com/BOYSABIO/muttmetrics/issues/217): press the power button. Everything else comes back by itself |

---

## Part C: when it misbehaves

| Symptom | Look at | Likely cause and fix |
|---|---|---|
| Groomer: page hangs | `sudo journalctl -u tailscaled -f \| grep Drop` while he reloads | **Port 80 drops:** he opened `http://` (or typed the name without `https://`); use the home-screen shortcut. **Port 443 drops:** the grant doesn't cover him; check Preview rules for his account. **Nothing:** his Tailscale isn't connected (switch it off and on) |
| Groomer: "can't find server" | his Tailscale app | Tailscale off, or "Use Tailscale DNS" off on the phone |
| Groomer: loads, saves fail | `journalctl -u muttmetrics-api -n 50`; `docker compose ps` | API or Postgres down. Failed saves wait as drafts on the phone |
| Everyone: nothing loads | `tailscale status` on the box, `serve status` | Box offline (power, network, USB disk: [#220](https://github.com/BOYSABIO/muttmetrics/issues/220)) |
| Deploy: "Connection refused" at step 9 | `curl -s http://127.0.0.1:8000/health` | If it answers, the deploy was fine. Usually the *previous* release's `deploy.py` ran (it's loaded before the checkout); re-run `--to` the same tag |
| Deploy: "working tree is dirty" | `git status --short` | Something edited the checkout; `git checkout -- .` (code only) and redeploy |
| `sudo` refuses `muttmetrics`'s password | the prompt | Working as intended: it has no password and no general sudo. `exit` to `<admin>` |
| SSH from the LAN times out | `journalctl -k \| grep host_fw` | Arriving through a subnet router (shows the router's address). Use `ssh <admin>@muttmetrics` |
| 🔴 *heartbeat is DOWN, signal did not arrive* | is the box on? `tailscale status` from another device | **Silence:** power, home internet, a frozen box, or the USB SSD. Nothing to do remotely if it's off (#217: press the button) |
| 🔴 *heartbeat is DOWN, failure signal* | `systemctl is-active muttmetrics-api caddy docker`; `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/api/services` | **The box is up, the app isn't:** API, Caddy or Postgres down. Restart the failed one; check its log |
| 🔴 *backup is DOWN* | `journalctl -u muttmetrics-backup -n 30` | **Failure signal:** the backup or its check failed. **No signal:** the timer didn't run (`systemctl list-timers muttmetrics-backup.timer`) |
| Backup unit failed | `systemctl status muttmetrics-backup`; `journalctl -u muttmetrics-backup` | Docker or Postgres down, or disk full; fix it and `sudo systemctl start muttmetrics-backup.service` |

**Debugging lessons:**

- **`tailscale ping` ignores the access rules.** A pong only proves the tunnel.
- **`tcpdump -i tailscale0` can't see `tailscale serve` traffic,** because it's handled inside `tailscaled`. Use the drop log instead.
- **A policy test copied from its rule repeats the rule's typo,** and then passes while protecting it.
- **`systemctl restart` returns before the service is listening.** Anything that checks it straight afterwards has to wait.
