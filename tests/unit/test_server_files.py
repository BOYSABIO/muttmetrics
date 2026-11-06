"""ops/server/ (#93): safe to publish, and still saying what the box relies on.

The folder holds reference copies of the home server's config. It's public, so
it must never pick up a secret or a home-network detail, and the few lines the
security model depends on (localhost bindings, the sandbox, the key header)
must not drift away silently.
"""

import ipaddress
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "ops" / "server"
FILES = sorted(p for p in SERVER.rglob("*") if p.is_file())

IPV4 = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})(?:/\d{1,2})?\b")
# Addresses that are fine to publish: loopback and the RFC 5737 documentation range
ALLOWED = [ipaddress.ip_network("127.0.0.0/8"), ipaddress.ip_network("192.0.2.0/24")]


def read(rel: str) -> str:
    return (SERVER / rel).read_text(encoding="utf-8")


def test_folder_is_not_empty():
    assert len(FILES) >= 10


@pytest.mark.parametrize("path", FILES, ids=lambda p: str(p.relative_to(SERVER)))
def test_no_private_addresses(path):
    for match in IPV4.finditer(path.read_text(encoding="utf-8")):
        try:
            addr = ipaddress.ip_address(match.group(1))
        except ValueError:
            continue  # e.g. a version number
        assert any(addr in net for net in ALLOWED), (
            f"{path.name}: {addr} looks like a real address; use a placeholder"
        )


@pytest.mark.parametrize("path", FILES, ids=lambda p: str(p.relative_to(SERVER)))
def test_no_tailnet_names_or_secrets(path):
    text = path.read_text(encoding="utf-8")
    assert not re.search(r"tail[0-9a-f]{4,}\.ts\.net", text), f"{path.name}: real tailnet name"
    assert not re.search(r"tskey-", text), f"{path.name}: Tailscale auth key"
    assert not re.search(r"(?m)^\s*(API_KEY|POSTGRES_PASSWORD|DATABASE_URL)\s*=", text), (
        f"{path.name}: secrets belong in the box's .env only"
    )


def test_api_listens_on_localhost_and_is_sandboxed():
    unit = read("systemd/muttmetrics-api.service")
    assert "--host 127.0.0.1" in unit
    assert "User=muttmetrics" in unit
    assert "ProtectSystem=strict" in unit
    assert "ReadWritePaths=/srv/muttmetrics" in unit
    assert "Restart=always" in unit


def test_caddy_is_localhost_only_and_replaces_the_key():
    caddyfile = read("caddy/Caddyfile")
    assert "bind 127.0.0.1" in caddyfile
    assert "header_up X-API-Key {env.API_KEY}" in caddyfile


def test_firewall_never_flushes_other_tables():
    conf = read("nftables/nftables.conf")
    assert "flush ruleset" not in conf.replace("`flush ruleset`", "")
    assert "policy drop;" in conf
    assert 'iifname "tailscale0" accept' in conf


def test_sudoers_allows_exactly_one_command():
    rules = [
        line
        for line in read("sudoers/muttmetrics-deploy").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert rules == [
        "muttmetrics ALL=(root) NOPASSWD: /usr/bin/systemctl restart muttmetrics-api caddy"
    ]


def test_restart_command_matches_sudoers():
    profile = read("profile/deploy-env.sh")
    assert 'MUTTMETRICS_RESTART_CMD="sudo systemctl restart muttmetrics-api caddy"' in profile


def test_postgres_stays_on_localhost():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert '"127.0.0.1:5432:5432"' in compose
