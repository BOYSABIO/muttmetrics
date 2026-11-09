# Runbook: the groomer's access

How the groomer reaches the app, what to tell him, and what to check when "the app doesn't work". The server side is [`home-server.md`](./home-server.md).

**Roles:** **User** = the groomer, capturing visits on his phone. **Owner** = the maintainer.

*History:* until 2026-11 the app ran from the maintainer's desktop for the phone trial ([#82](https://github.com/BOYSABIO/muttmetrics/issues/82)): Vite preview on `:5174`, reached through a subnet route. That path is retired. The app now runs on the always-on home server ([#93](https://github.com/BOYSABIO/muttmetrics/issues/93)).

---

## 0. The path

```text
User's phone (Tailscale app on, mobile data or any Wi-Fi)
      │  https://muttmetrics.<tailnet>        ← the full name, with https://
      ▼
the box's own Tailscale node (tag:muttmetrics), port 443 only
      ▼
Caddy → API → Postgres, all on the box's localhost
```

| Thing | Value |
|---|---|
| URL | `https://muttmetrics.<tailnet>`, as a **home-screen shortcut** |
| Tailscale grant | `group:<groomer-group>` → `tag:muttmetrics`, `tcp:443` only |
| Policy test | accept `tag:muttmetrics:443`; deny `:22`, `:8000`, `:5432` |
| His device | **key expiry disabled** in the admin console (otherwise it quietly logs out after months) |

## 1. One-time setup for a new phone

1. Install the Tailscale app and sign in with the account that's in `group:<groomer-group>` (as a **Member**, not an Admin).
2. Owner: in the admin console, disable key expiry on that device.
3. With Tailscale on, open **`https://muttmetrics.<tailnet>`**. Type `https://`: without it the browser tries `http://` (port 80), which isn't allowed, and the page just hangs.
4. **Add to Home Screen** from that page, so `https://` is saved and he never types it again. Delete any old shortcut.

**Check:** Owner, Admin console → Access controls → **Preview rules** → his account shows `tag:muttmetrics:443`.

## 2. User's phone checklist

Send this part to User; it is all he needs.

1. **Open** the MuttMetrics shortcut (Tailscale must be on). The first screen is **This week**; tap **+** to start a visit.
2. **Find the dog:** type part of the name → tap the right row (the owner name is shown next to it).
3. **New client** (first visit only): tap **+** next to the search → type the owner name. If they already exist, tap **Use**. Otherwise continue with the pet's name (phone optional). After **Save visit**, you can start another dog from the same owner without searching again.
4. **Step 1 — before photo:** **Take photo** or **Choose photo**. Optional, but it's the picture of how the dog arrived.
5. **Step 2 — timer:** **Start** when you start the groom, **Stop** when you finish. If you forget, type the minutes in by hand. Minutes is the one number that matters.
6. **Step 3 — details and after photo:** the date is already today. Condition score and "what surprised me" are optional but useful. Tap **Save visit** and wait for the confirmation.
7. **If anything fails:** nothing is lost. A visit that didn't save stays on the phone as a draft; open the app again later and save it. If in doubt, write the dog and the minutes on paper and tell Owner.

**Must fill:** the dog and the minutes. **Everything else, photos included, can be skipped.** A failed photo upload never blocks the save; don't re-enter the visit.

A reload mid-groom keeps the timer (the draft lives in the browser, [#88](https://github.com/BOYSABIO/muttmetrics/issues/88)), but a chosen photo has to be picked again. Photos are stripped of metadata (including GPS) and downscaled on the server ([`photos.md`](./photos.md)).

## 3. Rules for Owner while User is working

The app is live all day now, so the risk is Owner, not the phone:

| Don't, during grooms | Why |
|---|---|
| Deploy (`ops/deploy.py`) | The restart takes seconds; a save in that moment becomes a draft he has to retry |
| Restore a backup or run `alembic` on the box | Changes his data underneath him |
| Change the Tailscale policy | A typo locks him out (it happened: a `433` for `443`) |

Deploys, restores and policy changes happen after hours.

## 4. Confirming visits landed

On the box, as `muttmetrics` in `/opt/muttmetrics`:

```bash
docker compose exec -T db psql -U muttmetrics -d muttmetrics -c "
SELECT v.visit_id, d.name AS pet, o.name AS owner, v.visit_date, v.actual_minutes
FROM visit v JOIN pet d ON d.pet_id = v.pet_id JOIN owner o ON o.owner_id = v.owner_id
WHERE v.visit_date = CURRENT_DATE ORDER BY v.visit_id;"
```

Compare with the grooms he actually did; weekly compliance is [`compliance.md`](./compliance.md). Corrections afterwards go through the Directory ([`enrichment.md`](./enrichment.md)).

## 5. "The app doesn't work"

Ask him first, in this order:

1. **Is Tailscale on?** Open the app; it should say Connected. If in doubt, switch it off and on.
2. **Did he use the shortcut?** A typed name without `https://` hangs.
3. **Does he have signal?** No signal = no app. Saves wait as drafts.

Often Owner already knows: if the app itself is broken, Healthchecks sends a 🔴 to Telegram within 5 minutes, and if the box has gone silent, within about 30 ([`home-server.md`](./home-server.md) §A5b).

Then Owner, on the box (details: [`home-server.md`](./home-server.md) Part C):

```bash
tailscale status | grep -i <his-device>                  # online? "active"/"idle", not "offline"
sudo journalctl -u tailscaled -f | grep -i drop          # while he reloads: which port gets dropped
systemctl is-active muttmetrics-api caddy docker         # is the app up?
```

| What the drop log shows | Meaning |
|---|---|
| `…:80 no rules matched` | He's on `http://`. Use the `https://` shortcut |
| `…:443 no rules matched` | The grant doesn't cover his account. Check Preview rules |
| Nothing, and his device is `offline` | His Tailscale isn't connected |
| Nothing, he's online, the services are up | Ask him to close the tab and open the shortcut again |

`tailscale ping <his-device>` only proves the tunnel (it ignores the rules), and `tcpdump` on `tailscale0` can't see this traffic. The drop log is the tool.
