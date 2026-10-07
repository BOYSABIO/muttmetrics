# Runbook: backups — running them, checking them, restoring from them

Operational reference for [#95](https://github.com/BOYSABIO/muttmetrics/issues/95). Related: [`photos.md`](./photos.md) (what is being backed up), [`privacy.md`](../architecture/privacy.md) (retention / client asks), [ADR-002](../architecture/adr/002-photo-storage.md) (why photos are files), [`scripts/README.md`](../../scripts/README.md) (script index).

---

## 0. What exists, and what it protects against


| What                   | How                                                    | Where                                       |
| ---------------------- | ------------------------------------------------------ | ------------------------------------------- |
| Database               | `pg_dump -Fc` — a fresh compressed archive every run   | `<BACKUP_ROOT>/db/muttmetrics-<stamp>.dump` |
| Photos                 | **additive** file copy — new files only, never deletes | `<BACKUP_ROOT>/photos/…`                    |
| Report of the last run | JSON                                                   | `<BACKUP_ROOT>/last-backup.json`            |
| Run log                | appended text                                          | `<BACKUP_ROOT>/backup.log`                  |


```env
BACKUP_ROOT=C:/muttmetrics-data/backups   # defaults to ~/muttmetrics-data/backups
```

**Be honest about the threat model.** Today every destination is on the same physical disk as the live data.


| Failure                                 | Covered? |
| --------------------------------------- | -------- |
| `docker compose down -v`                | yes      |
| A migration that drops the wrong column | yes      |
| A bad `DELETE` during enrichment        | yes      |
| Postgres corruption                     | yes      |
| The drive dies                          | **no**   |
| Theft, fire, ransomware                 | **no**   |


The first four are the ones that have nearly happened. The rest needs a second machine, which arrives with the shop box ([#93](https://github.com/BOYSABIO/muttmetrics/issues/93)): it will back up to the maintainer's PC over Tailscale, and that is a second `--extra-dest`, not a rewrite.

## 1. Running a backup

```bash
python scripts/backup.py
```

Options: `--extra-dest PATH` (repeatable, for a second destination), `--skip-photos`, `--no-prune`.

Every run: dumps the database, **verifies the archive is readable before writing it** (`pg_restore --list`), writes the dump, copies any new photos, prunes old dumps, and updates `last-backup.json` and `backup.log`.

The script runs `docker compose` with the repo as its working directory regardless of where it is called from — so a scheduler that starts in `C:\Windows\System32` still works.

**Current practice:** run by hand, roughly daily. Fine at about one groom a day; **schedule it before volume picks up** (§4), because "I'll remember" is how backups die.

## 2. Checking that backups are still happening

```bash
python scripts/backup_check.py
python scripts/backup_check.py --max-age-hours 24
```

Prints the age of the last run and exits **non-zero** when it is stale or missing. It also verifies that the dump named in the status file actually exists, because a status report is a claim and the directory is the fact.

Run it after any gap — a holiday, a reinstall, a Python upgrade. Automated alerting is iceboxed until the shop box exists ([#104](https://github.com/BOYSABIO/muttmetrics/issues/104)); the exit code is the hook it will use.

## 3. Retention


| Tier   | Rule                                           |
| ------ | ---------------------------------------------- |
| Daily  | every dump from the last **14 days**           |
| Weekly | **Sunday** dumps for **8 weeks**               |
| Photos | additive copy — **never** pruned automatically |


Two weeks catches "I broke it last Tuesday"; eight Sundays catches the subtler "this has been wrong for a month". Dumps are ~30KB today, so this costs nothing.

Photos are never pruned because a mirror would propagate an accidental deletion into the backup — the opposite of the job. The consequence is that **honouring a deletion request needs the backup copy removed too** (§6).

Pruning only ever touches files matching `muttmetrics-*.dump` whose timestamp it can parse. Anything else in the folder — a manual `.sql` snapshot, say — is left alone by design.

## 4. Scheduling it (not yet enabled — do this before the salon opens)



### Windows (current host)

```powershell
# Resolve absolute paths once on the host (Task Scheduler needs them; don't paste a personal path into the repo):
#   $py   = (Resolve-Path .\.venv\Scripts\python.exe).Path
#   $script = (Resolve-Path .\scripts\backup.py).Path
schtasks /Create /TN "MuttMetrics backup" /SC DAILY /ST 21:00 /F `
  /TR "`"$py`" `"$script`""
```

Then open Task Scheduler and set two things the command line cannot:

- **Settings → "Run task as soon as possible after a scheduled start is missed."** Without it, a PC that is off at 21:00 skips that day silently, forever.
- **General → "Run only when user is logged on" — keep this ON.** This is the opposite of the usual advice, and it is correct here: Docker Desktop only runs inside the logged-in session, so a task running without a login would find no Docker and fail every night.

Verify it as the scheduler, not as yourself:

```powershell
schtasks /Run /TN "MuttMetrics backup"
Get-Content C:\muttmetrics-data\backups\backup.log -Tail 10
python scripts/backup_check.py
```

The log file is the proof it ran unattended.

### Linux (shop box, #93)

Same script, no changes:

```ini
# /etc/systemd/system/muttmetrics-backup.service
[Service]
Type=oneshot
WorkingDirectory=/opt/muttmetrics
ExecStart=/opt/muttmetrics/.venv/bin/python scripts/backup.py
```

```ini
# /etc/systemd/system/muttmetrics-backup.timer
[Unit]
Description=Daily MuttMetrics backup

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl enable --now muttmetrics-backup.timer
systemctl list-timers muttmetrics-backup
```

`Persistent=true` is the systemd version of "run a missed job": if the box was off, it runs on the next boot.

## 5. Restoring — the drill, and the real thing

Do this once after any change to the backup, and before anything risky (a migration, [#98](https://github.com/BOYSABIO/muttmetrics/issues/98)).

### Drill: restore into a scratch database

```bash
# 1. counts from the live database, to compare against
docker compose exec db psql -U muttmetrics -d muttmetrics -c "SELECT (SELECT count(*) FROM owner) AS owners, (SELECT count(*) FROM dog) AS dogs, (SELECT count(*) FROM visit) AS visits, (SELECT count(*) FROM photo) AS photos;"

# 2. a scratch database, and the dump copied into the container
#    drop it first: restoring into a database that already holds the same data
#    would make the counts match without the restore doing anything - a pass for
#    the wrong reason.
docker compose exec db dropdb -U muttmetrics --if-exists muttmetrics_restore_test
docker compose exec db createdb -U muttmetrics muttmetrics_restore_test
docker compose cp C:/muttmetrics-data/backups/db/muttmetrics-<stamp>.dump db:/tmp/restore.dump

# 3. restore into it
docker compose exec db pg_restore -U muttmetrics -d muttmetrics_restore_test /tmp/restore.dump

# 4. same counts, from the restored copy
docker compose exec db psql -U muttmetrics -d muttmetrics_restore_test -c "SELECT (SELECT count(*) FROM owner) AS owners, (SELECT count(*) FROM dog) AS dogs, (SELECT count(*) FROM visit) AS visits, (SELECT count(*) FROM photo) AS photos;"

# 5. clean up
docker compose exec db dropdb -U muttmetrics muttmetrics_restore_test
```

The numbers should match (allowing for rows added since the dump). **Record the result in the drill log** (below).

### The real thing: restoring over the live database

```bash
python scripts/backup.py            # dump the current state first, whatever state it is in
docker compose exec db dropdb -U muttmetrics muttmetrics
docker compose exec db createdb -U muttmetrics muttmetrics
docker compose cp <dump> db:/tmp/restore.dump
docker compose exec db pg_restore -U muttmetrics -d muttmetrics /tmp/restore.dump
alembic current                     # confirm the schema version matches the code
```

**Photos restore by copying** `<BACKUP_ROOT>/photos/` back over `PHOTO_ROOT` — the keys in the database are relative, so nothing in the rows needs changing.

After any restore, run `scripts/photo_sweep.py` (files with no row) and spot-check a `GET /photos/{id}` (rows with no file).

### Drill log

Results live in `docs/notes/backup-drills.md`, which is **gitignored** — row counts are business data (how many clients, how many grooms), and this runbook is public. Record the date, the dump used, the four counts on both sides, and whether they matched.

Run a drill after any change to `scripts/backup.py`, before a migration that touches existing data, and at least once a quarter otherwise.

## 6. Deleting a client's photos, including from backups

`scripts/photo_purge.py` removes the live file and the row. The backup copy is additive and has to be removed too:

```bash
python scripts/photo_purge.py --owner-id 42            # review
python scripts/photo_purge.py --owner-id 42 --apply    # live file + row
# then remove the same relative keys under <BACKUP_ROOT>/photos/
```

The key is the same relative path in both places — which is why it is stored relative. Database backups containing that client's rows age out within 14 days; say so rather than claiming instant total erasure (`[privacy.md](../architecture/privacy.md)`).

## 7. Troubleshooting


| Symptom                                            | Cause                                                                         | Fix                                                          |
| -------------------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------ |
| `ERROR: docker not found on PATH`                  | Docker Desktop not running, or the task runs without a login                  | Start Docker; keep "run only when user is logged on"         |
| `ERROR: pg_dump failed`                            | The db container is down                                                      | `docker compose ps`, then `docker compose up -d`             |
| `ERROR: dump is not readable`                      | The archive is truncated — **the run wrote nothing, by design**               | Check disk space; re-run                                     |
| `backup_check` says no status file                 | The backup has never run against this destination                             | Run it once                                                  |
| `backup_check` FAILs on age                        | It has stopped — scheduled task disabled, machine off, venv broken            | Fix the cause, run it, re-check                              |
| Dumps pile up                                      | `--no-prune` in the scheduled command                                         | Remove the flag                                              |
| A dump has a date that does not match its contents | Someone copied a file to fake a name (this happened while testing the pruner) | Delete it — a backup whose name lies is worse than no backup |


