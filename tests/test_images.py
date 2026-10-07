"""Image ingest: validation, EXIF stripping, downscaling."""

from io import BytesIO

import pytest
from PIL import Image

from muttmetrics.media.images import MAX_EDGE, MAX_UPLOAD_BYTES, ImageRejected, process_upload


def _image_bytes(width: int, height: int, fmt: str = "PNG") -> bytes:
    """Pillow builds its own test fixtures - no binary files in the repo."""
    buf = BytesIO()
    Image.new("RGB", (width, height), "red").save(buf, format=fmt)
    return buf.getvalue()


def test_large_image_is_downscaled_to_jpeg() -> None:
    """Long edge is capped and the output is always JPEG."""
    img = Image.open(BytesIO(process_upload(_image_bytes(4000, 3000))))

    assert img.format == "JPEG"
    assert img.size == (MAX_EDGE, 1200)


def test_small_image_is_not_upscaled() -> None:
    """Thumbnail() never enlarges - small photo stays small."""
    img = Image.open(BytesIO(process_upload(_image_bytes(320, 240))))

    assert img.size == (320, 240)


def test_metadata_is_stripped() -> None:
    """No EXIF survives - that is how GPS from a phone is removed."""
    exif = Image.Exif()
    exif[0x010F] = "MuttPhone"  # Make

    source = BytesIO()
    Image.new("RGB", (100, 100), "blue").save(source, format="PNG", exif=exif)
    assert dict(Image.open(BytesIO(source.getvalue())).getexif()) != {}

    out = process_upload(source.getvalue())
    assert dict(Image.open(BytesIO(out)).getexif()) == {}


def test_transparent_png_is_flattened() -> None:
    """RGBA input would crash the JPEG encoder without the convert step."""
    buf = BytesIO()
    Image.new("RGBA", (200, 200), (255, 0, 0, 128)).save(buf, format="PNG")

    assert Image.open(BytesIO(process_upload(buf.getvalue()))).mode == "RGB"


def test_non_image_is_rejected() -> None:
    with pytest.raises(ImageRejected):
        process_upload(b"definitely not an image")


def test_empty_upload_is_rejected() -> None:
    with pytest.raises(ImageRejected):
        process_upload(b"")


def test_oversized_upload_is_rejected() -> None:
    """Checked against the actual bytes, not a header we were told to trust."""
    with pytest.raises(ImageRejected):
        process_upload(b"x" * (MAX_UPLOAD_BYTES + 1))
