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
