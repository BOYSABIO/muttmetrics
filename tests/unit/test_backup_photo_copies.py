"""ops/backup.py photo copies are owner-only, whatever the source's mode (0.6.7).

shutil.copy2 copies permission bits too, so the umask set in main() didn't
apply to photos: a 644 original made a 644 backup copy.
"""

import os
import stat
from pathlib import Path

import pytest
from ops.backup import copy_new_photos

pytestmark = pytest.mark.skipif(os.name != "posix", reason="file modes are POSIX-only")


def test_copies_are_owner_only_and_skips_existing(tmp_path: Path) -> None:
    live = tmp_path / "photos"
    (live / "2026" / "11").mkdir(parents=True)
    src = live / "2026" / "11" / "a.jpg"
    src.write_bytes(b"jpeg")
    src.chmod(0o644)
    dest = tmp_path / "backup" / "photos"

    assert copy_new_photos(live, dest) == (1, 0)
    copy = dest / "2026" / "11" / "a.jpg"
    assert copy.read_bytes() == b"jpeg"
    assert stat.S_IMODE(copy.stat().st_mode) == 0o600

    # Additive: a second run copies nothing and leaves the copy alone
    assert copy_new_photos(live, dest) == (0, 1)
