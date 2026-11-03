"""Backend + SPA version strings stay lockstep (#197)."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from muttmetrics import __version__ as package_version

ROOT = Path(__file__).resolve().parents[2]


def _pyproject_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _frontend_version() -> str:
    data = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    return str(data["version"])


def _init_version() -> str:
    text = (ROOT / "src" / "muttmetrics" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    assert match, "__version__ not found in src/muttmetrics/__init__.py"
    return match.group(1)


def test_app_versions_match() -> None:
    assert _pyproject_version() == _frontend_version() == _init_version() == package_version
