"""Photo upload, listing and serving"""

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from muttmetrics.api.app import create_app
from muttmetrics.images import MAX_UPLOAD_BYTES

API_KEY = "test-api-key"
AUTH = {"X-API-KEY": API_KEY}


@pytest.fixture(autouse=True)
def photo_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Never write into the real photo directory."""
    monkeypatch.setenv("PHOTO_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://muttmetrics:muttmetrics@127.0.0.1:5432/muttmetrics",
    )
    monkeypatch.setenv("API_KEY", API_KEY)
    return TestClient(create_app())


@pytest.fixture
def visit_id(client: TestClient) -> int:
    """A real owner -> dog -> visit chain to hang photos on."""
    import uuid

    suffix = uuid.uuid4().hex[:8]

    owner = client.post("/owners", json={"name": f"Photo Owner {suffix}"}, headers=AUTH)
    owner_id = owner.json()["owner_id"]

    dog = client.post(
        "/dogs",
        json={"owner_id": owner_id, "name": f"Photo Dog {suffix}"},
        headers=AUTH,
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
        headers=AUTH,
    )
    assert visit.status_code == 201
    return visit.json()["visit_id"]


def _png(width: int, height: int) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (width, height), "red").save(buf, format="PNG")
    return buf.getvalue()


def _upload(client: TestClient, visit_id: int, data: bytes, kind: str = "intake"):
    return client.post(
        f"/visits/{visit_id}/photos",
        files={"file": ("bella.png", data, "image/png")},
        data={"kind": kind},
        headers=AUTH,
    )


def test_upload_returns_metadata_and_shrinks_the_image(client: TestClient, visit_id: int) -> None:
    original = _png(3000, 2000)
    response = _upload(client, visit_id, original)

    assert response.status_code == 201
    body = response.json()
    assert body["kind"] == "intake"
    assert body["visit_id"] == visit_id
    assert body["content_type"] == "image/jpeg"
    assert body["byte_size"] < len(original)
    assert "storage_key" not in body  # internal - never leaves the API


def test_upload_writes_exactly_one_file(
    client: TestClient, visit_id: int, photo_root: Path
) -> None:
    _upload(client, visit_id, _png(800, 600))

    files = [p for p in photo_root.rglob("*") if p.is_file()]
    assert len(files) == 1
    assert files[0].suffix == ".jpg"


def test_get_photo_returns_jpeg_bytes(client: TestClient, visit_id: int) -> None:
    photo_id = _upload(client, visit_id, _png(800, 600)).json()["photo_id"]

    response = client.get(f"/photos/{photo_id}", headers=AUTH)

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content[:2] == b"\xff\xd8"  # JPEG magic number
    assert Image.open(BytesIO(response.content)).format == "JPEG"


def test_list_visit_photos(client: TestClient, visit_id: int) -> None:
    _upload(client, visit_id, _png(400, 400), kind="intake")
    _upload(client, visit_id, _png(400, 400), kind="after")

    response = client.get(f"/visits/{visit_id}/photos", headers=AUTH)

    assert response.status_code == 200
    assert [row["kind"] for row in response.json()] == ["intake", "after"]


def test_non_image_is_415_and_stores_nothing(
    client: TestClient, visit_id: int, photo_root: Path
) -> None:
    response = _upload(client, visit_id, b"definitely not an image")

    assert response.status_code == 415
    assert list(photo_root.rglob("*.jpg")) == []
    assert client.get(f"/visits/{visit_id}/photos", headers=AUTH).json() == []


def test_oversized_upload_is_413(client: TestClient, visit_id: int) -> None:
    response = _upload(client, visit_id, b"x" * (MAX_UPLOAD_BYTES + 1))

    assert response.status_code == 413


def test_unknown_visit_is_404(client: TestClient) -> None:
    assert _upload(client, 999_999, _png(100, 100)).status_code == 404


def test_upload_requires_api_key(client: TestClient, visit_id: int) -> None:
    """These routes serve client photos - unauthenticated must not work."""
    response = client.post(
        f"/visits/{visit_id}/photos",
        files={"file": ("bella.png", _png(100, 100), "image/png")},
    )
    assert response.status_code == 401


def test_get_photo_requires_api_key(client: TestClient, visit_id: int) -> None:
    photo_id = _upload(client, visit_id, _png(100, 100)).json()["photo_id"]

    assert client.get(f"/photos/{photo_id}").status_code == 401
