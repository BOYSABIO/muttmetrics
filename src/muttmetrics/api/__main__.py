"""Dev server entry: python -m muttmetrics.api

Defaults: reload only under src/ (avoids watching .venv on Windows).
"""

from pathlib import Path

import uvicorn

from muttmetrics.config import get_settings


def main() -> None:
    """Run uvicorn with safe reload defaults for local development."""
    # Fail before binding the port if API_KEY is missing/insecure (#187).
    get_settings()
    # .../src/muttmetrics/api/__main__.py → parents[2] == .../src
    src_dir = Path(__file__).resolve().parents[2]
    uvicorn.run(
        "muttmetrics.api.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[str(src_dir)],
    )


if __name__ == "__main__":
    main()
