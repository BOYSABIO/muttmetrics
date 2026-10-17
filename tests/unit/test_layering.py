"""Package layering rule (#180).

``muttmetrics.api`` is the HTTP layer. Everything else (priors, seed, media,
services, the ops scripts, Alembic) must work without it, so a CLI never drags
in FastAPI and HTTP concerns never leak into domain code. Shared logic lives
in ``muttmetrics.services``.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "muttmetrics"


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append(node.module)
    return found


def _non_api_files() -> list[Path]:
    files = [p for p in PACKAGE.rglob("*.py") if "api" not in p.relative_to(PACKAGE).parts]
    files += list((ROOT / "ops").glob("*.py"))
    files += list((ROOT / "alembic").rglob("*.py"))
    return files


def test_nothing_outside_api_imports_api() -> None:
    offenders = [
        f"{path.relative_to(ROOT)} imports {name}"
        for path in _non_api_files()
        for name in _imports(path)
        if name == "muttmetrics.api" or name.startswith("muttmetrics.api.")
    ]
    assert offenders == [], "move shared code to muttmetrics.services:\n" + "\n".join(offenders)
