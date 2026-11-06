# Runbook: backups — running them, checking them, restoring from them

Operational reference for [#95](https://github.com/BOYSABIO/muttmetrics/issues/95). Related: [`photos.md`](./photos.md) (what is being backed up), [`privacy.md`](../architecture/privacy.md) (retention / client asks), [ADR-002](../architecture/adr/002-photo-storage.md) (why photos are files), [`ops/README.md`](../../ops/README.md) (script index).

---

## 0. What exists, and what it protects against


| What                   | How                                                    | Where                                       |
| ---------------------- | ------------------------------------------------------ | ------------------------------------------- |
| Database               | `pg_dump -Fc` — a fresh compressed archive every run   | `<BACKUP_ROOT>/db/muttmetrics-<stamp>.dump` |
| Photos                 | **additive** file copy — new files only, never deletes | `<BACKUP_ROOT>/photos/…`                    |
| Report of the last run | JSON                                                   | `<BACKUP_ROOT>/last-backup.json`            |
| Run log                | appended text                                          | `<BACKUP_ROOT>/backup.log`                  |


```env
BACKUP_ROOT=/srv/muttmetrics/backups   # the home server; defaults to ~/muttmetrics-data/backups
```

**Where it runs:** the home server ([#93](https://github.com/BOYSABIO/muttmetrics/issues/93), [`home-server.md`](./home-server.md)), nightly, as the `muttmetrics` account. The dev PC doesn't back up: its database holds synthetic data only ([#222](https://github.com/BOYSABIO/muttmetrics/issues/222)).

**Be honest about the threat model.** Every destination on the box is on the same physical disk as the live data (one SSD).


| Failure                                 | Covered? |
| --------------------------------------- | -------- |
| `docker compose down -v`                | yes      |
| A migration that drops the wrong column | yes      |
| A bad `DELETE` during enrichment        | yes      |
| Postgres corruption                     | yes      |
| The drive dies                          | **no**   |
| Theft, fire, ransomware                 | **no**   |


The first four are the ones that have nearly happened. The last two need a copy on another disk, outside the house: an encrypted drive as a second `--extra-dest`, not a rewrite ([#221](https://github.com/BOYSABIO/muttmetrics/issues/221)).

## 1. Running a backup

```bash
python ops/backup.py
```

Options: `--extra-dest PATH` (repeatable, for a second destination), `--skip-photos`, `--no-prune`.

Every run: dumps the database, **verifies the archive is readable before writing it** (`pg_restore --list`), writes the dump, copies any new photos, prunes old dumps, and updates `last-backup.json` and `backup.log`.

The script runs `docker compose` with the repo as its working directory regardless of where it is called from, so a scheduler still works. Everything it writes is owner-only (umask 077), whoever runs it.

**Current practice:** the systemd timer runs it every night at 00:30 (§4), and `ops/deploy.py` runs it before every deploy. By hand on the box: `sudo systemctl start muttmetrics-backup.service`.

## 2. Checking that backups are still happening

```bash
python ops/backup_check.py
python ops/backup_check.py --max-age-hours 24
```

Prints the age of the last run and exits **non-zero** when it is stale or missing. It also verifies that the dump named in the status file actually exists, because a status report is a claim and the directory is the fact.

Run it after any gap — a holiday, a reinstall, a Python upgrade. Automated alerting comes after the home server ([#104](https://github.com/BOYSABIO/muttmetrics/issues/104)); the exit code is the hook it will use.

## 3. Retention


| Tier   | Rule                                           |
| ------ | ---------------------------------------------- |
| Daily  | every dump from the last **14 days**           |
| Weekly | **Sunday** dumps for **8 weeks**               |
| Photos | additive copy — **never** pruned automatically |


Two weeks catches "I broke it last Tuesday"; eight Sundays catches the subtler "this has been wrong for a month". Dumps are ~30KB today, so this costs nothing.

Photos are never pruned because a mirror would propagate an accidental deletion into the backup — the opposite of the job. The consequence is that **honouring a deletion request needs the backup copy removed too** (§6).

Pruning only ever touches files matching `muttmetrics-*.dump` whose timestamp it can parse. Anything else in the folder — a manual `.sql` snapshot, say — is left alone by design.

## 4. Scheduling it (home server)

Installed from [`ops/server/systemd/`](../../ops/server/systemd/) ([`home-server.md`](./home-server.md) A5):

- **`muttmetrics-backup.service`:** runs `ops/backup.py` as `muttmetrics` (needs the `docker` group, which is root-equivalent, so nobody else gets it), then `ops/backup_check.py --max-age-hours 1` as `ExecStartPost`. If the backup *or* the check fails, the unit shows as **failed**, which is what monitoring watches ([#104](https://github.com/BOYSABIO/muttmetrics/issues/104)).
- **`muttmetrics-backup.timer`:** `OnCalendar=*-*-* 00:30`, after midnight and before the 04:30 update-reboot window. `Persistent=true` is systemd's "run a missed job": if the box was off, it runs at the next boot.

```bash
sudo systemctl enable --now muttmetrics-backup.timer
systemctl list-timers muttmetrics-backup.timer --no-pager      # next run
journalctl -u muttmetrics-backup -n 8 --no-pager               # last run, ends in "OK"
```

*History:* before #93 the capture host was a Windows desktop with a Task Scheduler entry. That path is retired.

## 5. Restoring — the drill, and the real thing

Do this once after any change to the backup, and before anything risky (a migration, [#98](https://github.com/BOYSABIO/muttmetrics/issues/98)).

On the box, as `muttmetrics` in `/opt/muttmetrics` (`sudo -iu muttmetrics`, `cd /opt/muttmetrics`). The dump is fed to `pg_restore` on **stdin**, so nothing needs copying into the container.

### Drill: restore into a scratch database

```bash
# 0. the newest dump
latest=$(ls -t /srv/muttmetrics/backups/db/muttmetrics-*.dump | head -1); echo "$latest"

# 1. counts from the live database, to compare against
docker compose exec db psql -U muttmetrics -d muttmetrics -c "SELECT (SELECT count(*) FROM owner) AS owners, (SELECT count(*) FROM pet) AS pets, (SELECT count(*) FROM visit) AS visits, (SELECT count(*) FROM photo) AS photos;"

# 2. a scratch database, and the dump copied into the container
#    drop it first: restoring into a database that already holds the same data
#    would make the counts match without the restore doing anything - a pass for
#    the wrong reason.
docker compose exec -T db dropdb -U muttmetrics --if-exists muttmetrics_restore_test
docker compose exec -T db createdb -U muttmetrics muttmetrics_restore_test

# 3. restore into it
docker compose exec -T db pg_restore -U muttmetrics -d muttmetrics_restore_test < "$latest"

# 4. same counts, from the restored copy
docker compose exec db psql -U muttmetrics -d muttmetrics_restore_test -c "SELECT (SELECT count(*) FROM owner) AS owners, (SELECT count(*) FROM pet) AS pets, (SELECT count(*) FROM visit) AS visits, (SELECT count(*) FROM photo) AS photos;"

# 5. clean up
docker compose exec -T db dropdb -U muttmetrics muttmetrics_restore_test

# 6. the photo backup is byte-for-byte the live photos
diff -r /srv/muttmetrics/photos /srv/muttmetrics/backups/photos && echo "photo backup identical"
```

The numbers should match (allowing for rows added since the dump). **Record the result in the drill log** (below).

### The real thing: restoring over the live database

```bash
sudo systemctl stop muttmetrics-api          # as <admin>: nothing may write while you restore
# then as muttmetrics, in /opt/muttmetrics:
.venv/bin/python ops/backup.py                 # dump the current state first, whatever state it is in
docker compose exec -T db dropdb -U muttmetrics muttmetrics
docker compose exec -T db createdb -U muttmetrics muttmetrics
docker compose exec -T db pg_restore -U muttmetrics -d muttmetrics < <dump>
.venv/bin/alembic current                      # confirm the schema version matches the code
# as <admin> again:
sudo systemctl start muttmetrics-api
```

**Photos restore by copying** `<BACKUP_ROOT>/photos/` back over `PHOTO_ROOT` — the keys in the database are relative, so nothing in the rows needs changing.

After any restore, run `ops/photo_sweep.py` (files with no row) and spot-check a `GET /photos/{id}` (rows with no file).

### Drill log

Results live in `docs/notes/backup-drills.md`, which is **gitignored** — row counts are business data (how many clients, how many grooms), and this runbook is public. Record the date, the dump used, the four counts on both sides, and whether they matched.

Run a drill after any change to `ops/backup.py`, before a migration that touches existing data, and at least once a quarter otherwise.

## 6. Deleting a client's photos, including from backups

`ops/photo_purge.py` removes the live file and the row. The backup copy is additive and has to be removed too:

```bash
python ops/photo_purge.py --owner-id 42            # review
python ops/photo_purge.py --owner-id 42 --apply    # live file + row
# then remove the same relative keys under <BACKUP_ROOT>/photos/
```

Once the off-site drive exists ([#221](https://github.com/BOYSABIO/muttmetrics/issues/221)), remove the same keys from its `photos/` the next time it's plugged in.

The key is the same relative path in both places — which is why it is stored relative. Database backups containing that client's rows age out within 14 days; say so rather than claiming instant total erasure (`[privacy.md](../architecture/privacy.md)`).

## 7. Troubleshooting


| Symptom                                            | Cause                                                                         | Fix                                                          |
| -------------------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------ |
| `ERROR: docker not found on PATH` / permission denied on the Docker socket | Docker not running, or the account isn't in the `docker` group | `systemctl is-active docker`; `id muttmetrics` shows `docker` |
| `ERROR: pg_dump failed`                            | The db container is down                                                      | `docker compose ps`, then `docker compose up -d`             |
| `ERROR: dump is not readable`                      | The archive is truncated — **the run wrote nothing, by design**               | Check disk space; re-run                                     |
| `backup_check` says no status file                 | The backup has never run against this destination                             | Run it once                                                  |
| `backup_check` FAILs on age                        | It has stopped: timer disabled, machine off, venv broken                     | `systemctl list-timers muttmetrics-backup.timer`; `journalctl -u muttmetrics-backup`; fix, run, re-check |
| `muttmetrics-backup.service` shows **failed**        | The backup or the check right after it failed                                 | `journalctl -u muttmetrics-backup -n 30`; fix; `sudo systemctl start muttmetrics-backup.service` |
| Dumps pile up                                      | `--no-prune` in the scheduled command                                         | Remove the flag                                              |
| A dump has a date that does not match its contents | Someone copied a file to fake a name (this happened while testing the pruner) | Delete it — a backup whose name lies is worse than no backup |


