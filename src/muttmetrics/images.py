"""Image ingest for capture photos.

Bytes in, bytes out - no filesystem, no database. Everything stored goes
through process_upload, so every photo on disk is a plain JPEG with no
embedded metadata.
"""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

# Teach Pillow to read iPhone HEIC. Once, at import.
register_heif_opener()

MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # generous for phone original
MAX_EDGE = 1600  # px on long edge after downscaling
JPEG_QUALITY = 85


class ImageRejected(ValueError):
    """The upload is not an image we are willing to store.

    ValueError because it means bad input from the caller, not a bug here -
    the API turns it into a 4xx, while anything else becomes 500.
    """


def process_upload(data: bytes) -> bytes:
    """Validate, rotate, strip metadata, downscale, re-encode as JPEG.

    Raises:
        ImageRejected: empty, too large, or not a decodable image.
    """
    if not data:
        raise ImageRejected("Empty upload")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ImageRejected(f"Upload is {len(data)} bytes; limit is {MAX_UPLOAD_BYTES}")

    out = BytesIO()
    try:
        with Image.open(BytesIO(data)) as opened:
            # Apply the orientation tag BEFORE metadata is dropped
            img = ImageOps.exif_transpose(opened)

            # JPEG cannot encode RGBA / palette modes (HEIC, PNG, GIF)
            img = img.convert("RGB")

            # In place, keeps aspect ratio, never upscales
            img.thumbnail((MAX_EDGE, MAX_EDGE))

            # No exif= argument: this is where GPS and timestamps are dropped
            img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    except UnidentifiedImageError as exc:
        raise ImageRejected("Not a readable image") from exc
    except Image.DecompressionBombError as exc:
        raise ImageRejected("Image dimensions are implausibly large") from exc
    except OSError as exc:
        raise ImageRejected(f"Could not process image: {exc}") from exc

    return out.getvalue()
