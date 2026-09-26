"""Local photo storage: keys, atomic writes, traversal defence."""

import re
from pathlib import Path

import pytest

from muttmetrics import storage


@pytest.fixture(autouse=True)
def photo_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point storage at a throwaway directory for every test in this file."""
    monkeypatch.setenv("PHOTO_ROOT", str(tmp_path))
    return tmp_path


def test_write_then_read_round_trip() -> None:
    """Bytes written under a key come back unchanged."""
    key = storage.build_key()
    storage.write_bytes(key, b"fake-jpeg-bytes")
    assert storage.read_bytes(key) == b"fake-jpeg-bytes"


def test_build_key_shape_and_uniqueness() -> None:
    """Keys are YYYY/MM/<32 hex>.jpg and never repeat."""
    keys = {storage.build_key() for _ in range(100)}
    assert len(keys) == 100

    pattern = re.compile(r"^\d{4}/\d{2}/[0-9a-f]{32}\.jpg$")
    assert all(pattern.match(key) for key in keys)


@pytest.mark.parametrize(
    "bad_key",
    [
        "../escape.jpg",
        "2026/09/../../escape.jpg",
        "..\\windows\\escape.jpg",
        "/etc/passwd",
        "",
    ],
)
def test_traversal_keys_are_rejected(bad_key: str) -> None:
    """A key must never address anything outside the photo root."""
    with pytest.raises(ValueError):
        storage.key_to_path(bad_key)


def test_write_leaves_no_temp_file(photo_root) -> None:
    """The atomic rename cleans up after itself."""
    key = storage.build_key()
    storage.write_bytes(key, b"bytes")

    leftovers = list(photo_root.rglob("*.tmp"))
    assert leftovers == []


def test_delete_is_true_once_then_false() -> None:
    """Deleting is idempotent: gone is a normal outcome, not an error."""
    key = storage.build_key()
    storage.write_bytes(key, b"bytes")

    assert storage.delete(key) is True
    assert storage.delete(key) is False

    with pytest.raises(FileNotFoundError):
        storage.read_bytes(key)
