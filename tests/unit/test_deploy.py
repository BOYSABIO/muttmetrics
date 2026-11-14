"""ops/deploy.py guards (#93): what it refuses, before anything touches the host."""

import pytest
from ops.deploy import check_tag_matches_version, main, validate_target


def test_needs_a_target():
    with pytest.raises(SystemExit, match="say what to deploy"):
        validate_target(None, allow_main=False)


def test_tag_and_main_are_exclusive():
    with pytest.raises(SystemExit, match="not both"):
        validate_target("v0.6.1", allow_main=True)


@pytest.mark.parametrize("tag", ["0.6.1", "v0.6", "v0.6.1-rc1", "main", "v0.6.1; rm -rf /"])
def test_rejects_non_release_tags(tag):
    with pytest.raises(SystemExit, match="not a release tag"):
        validate_target(tag, allow_main=False)


def test_accepts_release_tag_or_main():
    validate_target("v0.6.1", allow_main=False)
    validate_target(None, allow_main=True)


def test_tag_must_match_version():
    check_tag_matches_version("v0.6.1", "0.6.1")
    with pytest.raises(SystemExit, match="tagged before the version bump"):
        check_tag_matches_version("v0.6.2", "0.6.1")


def test_dry_run_changes_nothing(capsys):
    # The dry run must not need git, the network, a DB or npm.
    assert main(["--to", "v0.6.1", "--dry-run", "--app-url", "http://127.0.0.1:8080"]) == 0
    out = capsys.readouterr().out
    assert "git checkout --quiet --detach v0.6.1" in out
    assert "git pull" not in out
    assert "/api/services" in out
    # backup happens before the code moves
    assert out.index("ops/backup.py") < out.index("git checkout")


def test_health_waits_for_the_restarted_api(monkeypatch):
    # Right after `systemctl restart` the API refuses connections for a moment,
    # then the old version may answer: neither is a failed deploy (#93).
    import urllib.error

    import ops.deploy as deploy

    answers = iter(
        [
            urllib.error.URLError(ConnectionRefusedError(111, "Connection refused")),
            {"status": "ok", "version": "0.6.1"},
            {"status": "ok", "version": "0.6.2"},
        ]
    )

    def fake_get_json(url):
        a = next(answers)
        if isinstance(a, Exception):
            raise a
        return a

    monkeypatch.setattr(deploy, "get_json", fake_get_json)
    monkeypatch.setattr(deploy.time, "sleep", lambda s: None)
    assert deploy.wait_for_health("http://x/health", "0.6.2", timeout=30)["version"] == "0.6.2"


def test_health_gives_up_after_the_timeout(monkeypatch):
    import urllib.error

    import ops.deploy as deploy

    def refused(url):
        raise urllib.error.URLError(ConnectionRefusedError(111, "Connection refused"))

    clock = iter(range(0, 1000, 10))
    monkeypatch.setattr(deploy, "get_json", refused)
    monkeypatch.setattr(deploy.time, "sleep", lambda s: None)
    monkeypatch.setattr(deploy.time, "monotonic", lambda: next(clock))
    with pytest.raises(SystemExit, match="after 30s"):
        deploy.wait_for_health("http://x/health", "0.6.2", timeout=30)


def test_proxy_check_treats_no_answer_as_zero(monkeypatch):
    import urllib.error

    import ops.deploy as deploy

    def refused(url, timeout):
        raise urllib.error.URLError(ConnectionRefusedError(111, "Connection refused"))

    monkeypatch.setattr(deploy.urllib.request, "urlopen", refused)
    assert deploy.get_status("http://x/api/services") == 0


# --- 0.7.1: the page itself must be servable --------------------------------


@pytest.mark.skipif(not hasattr(__import__("os"), "umask"), reason="POSIX umask")
def test_spa_builds_under_umask_022_and_restores_the_shells(monkeypatch):
    """0.7.0 deployed from a shell with `umask 077`: dist/ came out owner-only
    and Caddy (another user) answered 403. The build now runs under 022."""
    import os

    import ops.deploy as deploy

    seen = []

    def fake_run(cmd, *, dry_run, cwd=None):
        current = os.umask(0)
        os.umask(current)
        seen.append((cmd[-1], current))

    monkeypatch.setattr(deploy, "run", fake_run)
    before = os.umask(0o077)
    try:
        deploy.build_spa(dry_run=False)
        after = os.umask(before)
    finally:
        os.umask(before)
    assert seen == [("ci", 0o022), ("build", 0o022)]
    assert after == 0o077  # the caller's umask is back


def test_app_check_fails_loudly_when_the_page_is_403(monkeypatch):
    import ops.deploy as deploy

    statuses = {"http://app/": 403, "http://app/api/services": 200}
    monkeypatch.setattr(deploy, "get_status", lambda url: statuses[url])
    monkeypatch.setattr(deploy.time, "sleep", lambda s: None)
    clock = iter([0.0, 0.0, 99.0, 99.0])
    monkeypatch.setattr(deploy.time, "monotonic", lambda: next(clock))
    with pytest.raises(SystemExit, match="can't read frontend/dist"):
        deploy.check_app("http://app", timeout=5)


def test_app_check_passes_page_then_proxy(monkeypatch):
    import ops.deploy as deploy

    calls = []

    def status(url):
        calls.append(url)
        return 200

    monkeypatch.setattr(deploy, "get_status", status)
    lines = deploy.check_app("http://app/", timeout=5)
    assert calls == ["http://app/", "http://app/api/services"]
    assert lines == ["  http://app/ → 200", "  http://app/api/services → 200"]
