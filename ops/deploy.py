"""One-command deploy for the capture host (#197, fixed for #93).

Stops at the first failure. No auto-deploy on merge: run this deliberately.

    python ops/deploy.py --to v0.6.1 --dry-run     # see the plan
    python ops/deploy.py --to v0.6.1               # salon release (or rollback)
    python ops/deploy.py --allow-main              # desktop drill from main

Order: guard → backup → move code (checkout tag / pull main) → read version →
install → migrate → SPA build → restart hook → health checks.

The version is read *after* the code moves, so a release that bumps it isn't
reported as a mismatch. A tag is checked out detached, which is why there is no
``git pull`` in the tag path: pull needs a branch and fails without one.

See docs/runbooks/release.md.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TAG_PATTERN = re.compile(r"^v\d+\.\d+\.\d+$")


def log(msg: str) -> None:
    print(msg, flush=True)


def run(
    cmd: list[str],
    *,
    dry_run: bool,
    cwd: Path | None = None,
) -> None:
    display = " ".join(cmd)
    if dry_run:
        log(f"  [dry-run] {display}")
        return
    log(f"  $ {display}")
    subprocess.run(cmd, cwd=str(cwd or REPO_ROOT), check=True)


def git_output(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=str(REPO_ROOT), text=True).strip()


def validate_target(tag: str | None, allow_main: bool) -> None:
    """Exactly one of --to vX.Y.Z or --allow-main, and a well-formed tag."""
    if tag and allow_main:
        raise SystemExit("Refusing: use either --to vX.Y.Z or --allow-main, not both.")
    if not tag and not allow_main:
        raise SystemExit(
            "Refusing: say what to deploy. --to vX.Y.Z for a release or rollback, "
            "--allow-main for a desktop drill."
        )
    if tag and not TAG_PATTERN.match(tag):
        raise SystemExit(f"Refusing: {tag!r} is not a release tag (expected vX.Y.Z).")


def check_tag_matches_version(tag: str, version: str) -> None:
    """A tag must ship the version it is named after (v0.6.1 → 0.6.1)."""
    if tag != f"v{version}":
        raise SystemExit(
            f"Refusing: tag {tag} contains version {version}. "
            "The release was tagged before the version bump, or on the wrong commit."
        )


def guard_clean_tree() -> None:
    if git_output("status", "--porcelain"):
        raise SystemExit(
            "Refusing: working tree is dirty. Commit, stash, or discard changes first."
        )


def guard_on_main() -> None:
    branch = git_output("rev-parse", "--abbrev-ref", "HEAD")
    if branch != "main":
        raise SystemExit(
            f"Refusing: --allow-main needs the main branch checked out (now {branch!r}). "
            "On the box, deploy a tag with --to instead."
        )


def fetch_and_verify_tag(tag: str) -> None:
    subprocess.run(["git", "fetch", "--tags", "origin"], cwd=str(REPO_ROOT), check=True)
    try:
        git_output("rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}")
    except subprocess.CalledProcessError:
        raise SystemExit(f"Refusing: tag {tag} not found on origin.") from None


def package_version() -> str:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_status(url: str) -> int:
    """HTTP status of a GET; 0 if nothing answered (refused, timeout)."""
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return 0


def wait_for_health(url: str, expected: str, timeout: float) -> dict:
    """Poll /health until it reports `expected`, or give up after `timeout` s.

    `systemctl restart` returns as soon as the new process has *started*, not
    when it's listening, so the first request right after it is usually
    refused. Retrying also rides out the old process answering for a moment.
    """
    deadline = time.monotonic() + timeout
    last = "no answer yet"
    while True:
        try:
            body = get_json(url)
            if body.get("version") == expected:
                return body
            last = f"version {body.get('version')!r}, want {expected!r}"
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as exc:
            last = str(exc)
        if time.monotonic() >= deadline:
            raise SystemExit(
                f"Health check failed at {url} after {timeout:.0f}s: {last}. "
                "Check `systemctl status muttmetrics-api` / the journal, "
                "or fix MUTTMETRICS_RESTART_CMD."
            )
        time.sleep(1)


def wait_for_status(url: str, want: int, timeout: float) -> int:
    """Poll until `url` returns `want`; returns the last status seen."""
    deadline = time.monotonic() + timeout
    while True:
        status = get_status(url)
        if status == want or time.monotonic() >= deadline:
            return status
        time.sleep(1)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--to",
        metavar="vX.Y.Z",
        help="release tag to deploy (also how you roll back: --to the previous tag)",
    )
    p.add_argument(
        "--allow-main",
        action="store_true",
        help="deploy the tip of main instead of a tag (desktop / drills only)",
    )
    p.add_argument("--dry-run", action="store_true", help="print the steps, change nothing")
    p.add_argument(
        "--skip-backup",
        action="store_true",
        help="skip ops/backup.py (emergency only — never for the salon)",
    )
    p.add_argument(
        "--health-url",
        default="http://127.0.0.1:8000/health",
        help="API health URL (default: local API)",
    )
    p.add_argument(
        "--health-timeout",
        type=float,
        default=30,
        metavar="SECONDS",
        help="how long to wait for the restarted services to answer (default: 30)",
    )
    p.add_argument(
        "--app-url",
        default=os.environ.get("MUTTMETRICS_APP_URL", ""),
        help=(
            "where the SPA server listens, e.g. http://127.0.0.1:8080 "
            "(default: $MUTTMETRICS_APP_URL). Used to prove the /api proxy injects the key."
        ),
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    dry = args.dry_run
    validate_target(args.to, args.allow_main)
    target = args.to or "main"
    log(f"MuttMetrics deploy → {target}" + (" (dry-run)" if dry else ""))

    # 1) Guard
    log("1. Guard")
    if dry:
        log(
            "  [dry-run] refuse a dirty tree; "
            + (f"fetch tags and check {target} exists" if args.to else "require branch main")
        )
    else:
        guard_clean_tree()
        if args.to:
            fetch_and_verify_tag(args.to)
        else:
            guard_on_main()
    log(f"   running now: {package_version()}")

    # 2) Backup first, with the code that's running now
    log("2. Backup")
    if args.skip_backup:
        log("  ! skipped (--skip-backup)")
    else:
        run([sys.executable, "ops/backup.py"], dry_run=dry)

    # 3) Move the code
    log("3. Code")
    if args.to:
        run(["git", "checkout", "--quiet", "--detach", args.to], dry_run=dry)
    else:
        run(["git", "pull", "--ff-only"], dry_run=dry)

    # 4) What we're deploying, read after the move
    if dry:
        log("4. Version: read from pyproject.toml after step 3")
        expected = None
    else:
        expected = package_version()
        log(f"4. Version: {expected}")
        if args.to:
            check_tag_matches_version(args.to, expected)

    # 5) Backend deps (runtime only; dev tools live on the desktop)
    log("5. Install backend")
    run([sys.executable, "-m", "pip", "install", "--quiet", "-e", "."], dry_run=dry)

    # 6) Migrate
    log("6. alembic upgrade head")
    run([sys.executable, "-m", "alembic", "upgrade", "head"], dry_run=dry)

    # 7) SPA build
    log("7. SPA build")
    npm = "npm.cmd" if os.name == "nt" else "npm"
    run([npm, "ci"], dry_run=dry, cwd=REPO_ROOT / "frontend")
    run([npm, "run", "build"], dry_run=dry, cwd=REPO_ROOT / "frontend")

    # 8) Restart services
    log("8. Restart services")
    restart_cmd = os.environ.get("MUTTMETRICS_RESTART_CMD", "").strip()
    if restart_cmd:
        # Shell form for the box (#93), e.g.
        # MUTTMETRICS_RESTART_CMD="sudo systemctl restart muttmetrics-api caddy"
        if dry:
            log(f"  [dry-run] shell: {restart_cmd}")
        else:
            log(f"  $ {restart_cmd}")
            subprocess.run(restart_cmd, shell=True, check=True, cwd=str(REPO_ROOT))
    else:
        log(
            "  No MUTTMETRICS_RESTART_CMD set — restart the API and the SPA server yourself "
            "(desktop: muttmetrics-api + npm run preview)."
        )

    # 9) Health
    log("9. Health")
    if dry:
        log(f"  [dry-run] GET {args.health_url} → version must match")
        if args.app_url:
            log(f"  [dry-run] GET {args.app_url}/api/services → 200 (proxy adds the key)")
        return 0

    body = wait_for_health(args.health_url, expected, args.health_timeout)
    log(f"  /health → {body}")

    if args.app_url:
        # /health needs no key, so it can't prove the proxy works. /services does.
        url = f"{args.app_url.rstrip('/')}/api/services"
        status = wait_for_status(url, 200, args.health_timeout)
        log(f"  {url} → {status}")
        if status != 200:
            raise SystemExit(
                f"SPA proxy check failed ({status or 'no answer'}). 401 = the SPA server "
                "isn't adding X-API-Key from API_KEY (#194); 502 or no answer = it isn't "
                "running or can't reach the API."
            )
    else:
        log("  (no --app-url / MUTTMETRICS_APP_URL: proxy check skipped)")

    log("Deploy OK.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"Deploy stopped: command failed with exit {exc.returncode}", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc
