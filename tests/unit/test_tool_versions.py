"""One ruff version everywhere (#179).

pre-commit runs the ruff pinned in .pre-commit-config.yaml; CI and local
`ruff` run the one pinned in pyproject.toml. If they differ, a commit can pass
the hook and then fail CI on formatting, or the other way round.
"""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _pyproject_ruff() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    for spec in data["project"]["optional-dependencies"]["dev"]:
        match = re.fullmatch(r"ruff==(\S+)", spec.strip())
        if match:
            return match.group(1)
    raise AssertionError("pyproject.toml must pin ruff exactly, e.g. ruff==0.17.1")


def _pre_commit_ruff() -> str:
    text = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    match = re.search(r"astral-sh/ruff-pre-commit\s*\n\s*rev:\s*v(\S+)", text)
    assert match, "ruff-pre-commit rev not found in .pre-commit-config.yaml"
    return match.group(1)


def test_ruff_versions_match() -> None:
    assert _pyproject_ruff() == _pre_commit_ruff()
