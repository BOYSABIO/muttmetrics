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
