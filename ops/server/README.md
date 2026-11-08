# Home server config (#93)

Reference copies of every config file on the MuttMetrics home server, so a rebuild means **copying files, not retyping them**. The full procedure, with a check after each step, is [`docs/runbooks/home-server.md`](../../docs/runbooks/home-server.md).

These files are **safe to commit**: no secrets, no home-network specifics. Placeholders mark what's local:

| Placeholder | Means | Where the real value lives |
|---|---|---|
| `<admin>` | the admin account's username | maintainer's private notes |
| `WORKSTATION = 192.0.2.10` | the workstation's LAN address (`192.0.2.0/24` is documentation-only, RFC 5737) | private notes |
| `<…-check-uuid>` | the Healthchecks.io ping URLs | only in `/etc/muttmetrics/healthchecks.env` on the box |
| `group:<groomer-group>` | the groomer's Tailscale group | the tailnet policy + private notes |

Secrets (`API_KEY`, `POSTGRES_PASSWORD`) live only in `/opt/muttmetrics/.env` on the box, which is generated there and never copied anywhere. `tests/unit/test_server_files.py` fails if a private address, a tailnet name or a secret-looking value lands in this folder.

## What goes where

| File here | Installs to | Mode | Step |
|---|---|---|---|
| `apt/20auto-upgrades` | `/etc/apt/apt.conf.d/20auto-upgrades` (same as `dpkg-reconfigure -plow unattended-upgrades` → Yes) | 644 | 1 |
| `apt/52muttmetrics-reboot` | `/etc/apt/apt.conf.d/52muttmetrics-reboot` | 644 | 1 |
| `tailscale/policy-snippet.hujson` | merged into the **tailnet policy** (admin console → JSON editor), not a file on the box | — | 2 |
| `ssh/10-muttmetrics-hardening.conf` | `/etc/ssh/sshd_config.d/10-muttmetrics-hardening.conf` | 644 | 1 |
| `nftables/nftables.conf` | `/etc/nftables.conf` | 755 | 2b |
| `docker/daemon.json` | `/etc/docker/daemon.json` | 644 | 3 |
| `systemd/muttmetrics-api.service` | `/etc/systemd/system/` | 644 | 3 |
| `caddy/caddy-muttmetrics.conf` | `/etc/systemd/system/caddy.service.d/muttmetrics.conf` | 644 | 3 |
| `caddy/Caddyfile` | `/etc/caddy/Caddyfile` | 644 | 3 |
| `sudoers/muttmetrics-deploy` | `/etc/sudoers.d/muttmetrics-deploy` | **440** | 3 |
| `profile/deploy-env.sh` | appended to `/home/muttmetrics/.profile` | — | 3 |
| `systemd/muttmetrics-backup.service` + `.timer` | `/etc/systemd/system/` | 644 | 5 |
| `monitoring/healthchecks.env.example` | `/etc/muttmetrics/healthchecks.env`, with the two real ping URLs | **600**, root | 5b |
| `systemd/muttmetrics-heartbeat.service` + `.timer` | `/etc/systemd/system/` | 644 | 5b |

Install from a checkout on the box (as the admin account), for example:

```bash
cd /opt/muttmetrics/ops/server
sudo install -m 644 systemd/muttmetrics-api.service /etc/systemd/system/
sudo install -m 440 sudoers/muttmetrics-deploy /etc/sudoers.d/ && sudo visudo -cf /etc/sudoers.d/muttmetrics-deploy
```

Files with a placeholder (`ssh/…`, `nftables/…`) get edited **after** copying, on the box.

## Keep them in sync

These are copies, not the source of truth on the box. If you change a file on the box, change it here in the same breath (and the other way round), or the next rebuild quietly undoes the fix. Automating that (Ansible) is a homelab project, not this repo.
