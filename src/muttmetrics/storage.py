"""Local filesystem storage for capture photos.

Callers deal in keys and bytes; only this module knows about paths. That is
what makes moving the photo root a config change instead of a migration.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from muttmetrics.config import get_settings


def photo_root() -> Path:
    """Configured root as an absolute, normalized path."""
    return get_settings().photo_root.expanduser().resolve()


def build_key(now: datetime | None = None) -> str:
    """New unique key: 'YYYY/MM/<uuid4hex>.jpg'.

    Month comes from upload time - the only input always available. Forward
    slashes always, so keys survive a move to a Linux host.
    """
    moment = now or datetime.now(UTC)
    return f"{moment:%Y/%m}/{uuid.uuid4().hex}.jpg"


def key_to_path(key: str) -> Path:
    """Absolute path for a key.

    Raises ValueError if the key would escape the photo root.
    """
    if not key or key.startswith("/") or "\\" in key or ".." in key.split("/"):
        raise ValueError(f"Invalid storage key: {key!r}")

    root = photo_root()
    candidate = (root / key).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError(f"Storage key escapes the photo root: {key!r}")
    return candidate


def write_bytes(key: str, data: bytes) -> None:
    """Write bytes for a key, atomically.

    Writes a temp file in the same directory (same filesystem - required for
    os.replace to be atomic), flushes it to disk, then replaces the target.
    A crash can leave a .tmp file; it can never leave a half-written photo.
    """
    path = key_to_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp = path.with_name(f"{path.name}.tmp")
    try:
        with open(tmp, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def read_bytes(key: str) -> bytes:
    """Bytes for a key. Raises FileNotFoundError if the file is gone"""
    return key_to_path(key).read_bytes()


def delete(key: str) -> bool:
    """Remove the file for a key. Returns False if it was already gone."""
    path = key_to_path(key)
    if not path.exists():
        return False
    path.unlink()
    return True


def sha256_of(data: bytes) -> str:
    """Hex digest for the photo.sha256 column."""
    return hashlib.sha256(data).hexdigest()
