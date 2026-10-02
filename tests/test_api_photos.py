"""Photo upload, listing and serving"""

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from muttmetrics.images import MAX_UPLOAD_BYTES


@pytest.fixture(autouse=True)
def photo_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Never write into the real photo directory."""
    monkeypatch.setenv("PHOTO_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def visit_id(client: TestClient, auth_headers: dict[str, str]) -> int:
    """A real owner -> dog -> visit chain to hang photos on."""
    import uuid

    suffix = uuid.uuid4().hex[:8]

    owner = client.post("/owners", json={"name": f"Photo Owner {suffix}"}, headers=auth_headers)
    owner_id = owner.json()["owner_id"]

    dog = client.post(
        "/dogs",
        json={"owner_id": owner_id, "name": f"Photo Dog {suffix}"},
        headers=auth_headers,
    )
    dog_id = dog.json()["dog_id"]

    visit = client.post(
        "/visits",
        json={
            "dog_id": dog_id,
            "owner_id": owner_id,
            "visit_date": "2026-09-27",
            "actual_minutes": 75,
        },
        headers=auth_headers,
    )
    assert visit.status_code == 201
    return visit.json()["visit_id"]


def _png(width: int, height: int) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (width, height), "red").save(buf, format="PNG")
    return buf.getvalue()


def _upload(
    client: TestClient,
    visit_id: int,
    data: bytes,
    auth_headers: dict[str, str],
    kind: str = "intake",
):
    return client.post(
        f"/visits/{visit_id}/photos",
        files={"file": ("bella.png", data, "image/png")},
        data={"kind": kind},
        headers=auth_headers,
    )


def test_upload_returns_metadata_and_shrinks_the_image(
    client: TestClient, visit_id: int, auth_headers: dict[str, str]
) -> None:
    original = _png(3000, 2000)
    response = _upload(client, visit_id, original, auth_headers)

    assert response.status_code == 201
    body = response.json()
    assert body["kind"] == "intake"
    assert body["visit_id"] == visit_id
    assert body["content_type"] == "image/jpeg"
    assert body["byte_size"] < len(original)
    assert "storage_key" not in body  # internal - never leaves the API


def test_upload_writes_exactly_one_file(
    client: TestClient, visit_id: int, photo_root: Path, auth_headers: dict[str, str]
) -> None:
    _upload(client, visit_id, _png(800, 600), auth_headers)

    files = [p for p in photo_root.rglob("*") if p.is_file()]
    assert len(files) == 1
    assert files[0].suffix == ".jpg"


def test_get_photo_returns_jpeg_bytes(
    client: TestClient, visit_id: int, auth_headers: dict[str, str]
) -> None:
    photo_id = _upload(client, visit_id, _png(800, 600), auth_headers).json()["photo_id"]

    response = client.get(f"/photos/{photo_id}", headers=auth_headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content[:2] == b"\xff\xd8"  # JPEG magic number
    assert Image.open(BytesIO(response.content)).format == "JPEG"


def test_list_visit_photos(client: TestClient, visit_id: int, auth_headers: dict[str, str]) -> None:
    _upload(client, visit_id, _png(400, 400), auth_headers, kind="intake")
    _upload(client, visit_id, _png(400, 400), auth_headers, kind="after")

    response = client.get(f"/visits/{visit_id}/photos", headers=auth_headers)

    assert response.status_code == 200
    assert [row["kind"] for row in response.json()] == ["intake", "after"]


def test_non_image_is_415_and_stores_nothing(
    client: TestClient, visit_id: int, photo_root: Path, auth_headers: dict[str, str]
) -> None:
    response = _upload(client, visit_id, b"definitely not an image", auth_headers)

    assert response.status_code == 415
    assert list(photo_root.rglob("*.jpg")) == []
    assert client.get(f"/visits/{visit_id}/photos", headers=auth_headers).json() == []


def test_oversized_upload_is_413(
    client: TestClient, visit_id: int, auth_headers: dict[str, str]
) -> None:
    response = _upload(client, visit_id, b"x" * (MAX_UPLOAD_BYTES + 1), auth_headers)

    assert response.status_code == 413


def test_unknown_visit_is_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    assert _upload(client, 999_999, _png(100, 100), auth_headers).status_code == 404


def test_upload_requires_api_key(client: TestClient, visit_id: int) -> None:
    """These routes serve client photos - unauthenticated must not work."""
    response = client.post(
        f"/visits/{visit_id}/photos",
        files={"file": ("bella.png", _png(100, 100), "image/png")},
    )
    assert response.status_code == 401


def test_get_photo_requires_api_key(
    client: TestClient, visit_id: int, auth_headers: dict[str, str]
) -> None:
    photo_id = _upload(client, visit_id, _png(100, 100), auth_headers).json()["photo_id"]

    assert client.get(f"/photos/{photo_id}").status_code == 401
