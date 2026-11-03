"""One-command deploy for the capture host (#197).

Stops at the first failure. Desktop today; OptiPlex (#93) later via
MUTTMETRICS_RESTART_CMD. No auto-deploy on merge — run this deliberately.

    python ops/deploy.py --dry-run
    python ops/deploy.py

Order: guard ref → backup → pull → install → migrate → SPA build →
restart hook → /health version check.

See docs/runbooks/release.md.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def log(msg: str) -> None:
    print(msg, flush=True)


def run(
    cmd: list[str],
    *,
    dry_run: bool,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> None:
    display = " ".join(cmd)
    if dry_run:
        log(f"  [dry-run] {display}")
        return
    log(f"  $ {display}")
    subprocess.run(
        cmd,
        cwd=str(cwd or REPO_ROOT),
        env=env,
        check=True,
    )


def git_output(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=str(REPO_ROOT),
        text=True,
    ).strip()


def refuse_dirty_or_bad_ref(*, allow_main: bool) -> str:
    """Return the ref name we are deploying from (tag or main)."""
    dirty = git_output("status", "--porcelain")
    if dirty:
        raise SystemExit(
            "Refusing: working tree is dirty. Commit, stash, or discard changes first."
        )
    try:
        tag = subprocess.check_output(
            ["git", "describe", "--tags", "--exact-match", "HEAD"],
            cwd=str(REPO_ROOT),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except subprocess.CalledProcessError:
        tag = ""

    branch = git_output("rev-parse", "--abbrev-ref", "HEAD")
    if tag.startswith("v"):
        log(f"Ref: tag {tag}")
        return tag
    if branch == "main" and allow_main:
        log("Ref: main (desktop / drill — prefer a v* tag for salon releases)")
        return "main"
    raise SystemExit(
        "Refusing: HEAD must be a v* tag (or main with --allow-main for drills). "
        f"Now on branch={branch!r} tag={tag or '(none)'}."
    )


def package_version() -> str:
    import tomllib

    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def health_version(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="print steps without running them",
    )
    p.add_argument(
        "--allow-main",
        action="store_true",
        help="allow deploying from main (drills / desktop); prefer a v* tag for salon",
    )
    p.add_argument(
        "--skip-backup",
        action="store_true",
        help="skip ops/backup.py (emergency only — not for salon)",
    )
    p.add_argument(
        "--skip-pull",
        action="store_true",
        help="skip git pull (already at the desired commit)",
    )
    p.add_argument(
        "--health-url",
        default="http://127.0.0.1:8000/health",
        help="URL to check after restart (default: local API)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    dry = args.dry_run
    log("MuttMetrics deploy (#197)" + (" — dry-run" if dry else ""))

    # 1) Guard
    if dry:
        log("1. Guard: refuse dirty tree; require v* tag or --allow-main")
    else:
        log("1. Guard")
        refuse_dirty_or_bad_ref(allow_main=args.allow_main)

    expected = package_version()
    log(f"   package version: {expected}")

    # 2) Backup first
    log("2. Backup")
    if args.skip_backup:
        log("  ! skipped (--skip-backup)")
    else:
        run([sys.executable, "ops/backup.py"], dry_run=dry)

    # 3) Pull
    log("3. git pull")
    if args.skip_pull:
        log("  ! skipped (--skip-pull)")
    else:
        run(["git", "pull", "--ff-only"], dry_run=dry)

    # 4) Install backend deps (editable + locked enough via pyproject)
    log("4. Install backend")
    run(
        [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
        dry_run=dry,
    )

    # 5) Migrate
    log("5. alembic upgrade head")
    run([sys.executable, "-m", "alembic", "upgrade", "head"], dry_run=dry)

    # 6) SPA build
    log("6. SPA build")
    npm = "npm.cmd" if os.name == "nt" else "npm"
    run([npm, "ci"], dry_run=dry, cwd=REPO_ROOT / "frontend")
    run([npm, "run", "build"], dry_run=dry, cwd=REPO_ROOT / "frontend")

    # 7) Restart services
    log("7. Restart services")
    restart_cmd = os.environ.get("MUTTMETRICS_RESTART_CMD", "").strip()
    if restart_cmd:
        # shell form for #93 systemd one-liners, e.g.
        # MUTTMETRICS_RESTART_CMD="sudo systemctl restart muttmetrics-api muttmetrics-caddy"
        if dry:
            log(f"  [dry-run] shell: {restart_cmd}")
        else:
            log(f"  $ {restart_cmd}")
            subprocess.run(restart_cmd, shell=True, check=True, cwd=str(REPO_ROOT))
    else:
        log(
            "  No MUTTMETRICS_RESTART_CMD set — restart API + SPA server yourself "
            "(desktop: stop/start muttmetrics-api and npm run preview; "
            "box #93: set the env to systemctl restart …)."
        )

    # 8) Health / version
    log("8. Health check")
    if dry:
        log(f"  [dry-run] GET {args.health_url} — expect version={expected}")
        return 0

    try:
        body = health_version(args.health_url)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise SystemExit(
            f"Health check failed at {args.health_url}: {exc}. "
            "Start/restart the API, then re-check, or fix MUTTMETRICS_RESTART_CMD."
        ) from exc

    got = body.get("version")
    log(f"  /health → {body}")
    if got != expected:
        raise SystemExit(
            f"Version mismatch: package={expected!r} /health.version={got!r}. "
            "Is the old API process still running?"
        )
    log("Deploy OK.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"Deploy stopped: command failed with exit {exc.returncode}", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc
