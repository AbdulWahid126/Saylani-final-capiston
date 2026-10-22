"""Secure image validation, dimension checking, and safe re-encoding for TASK-014."""

import io
import os
import re
import uuid
from dataclasses import dataclass

from PIL import Image, ImageOps

from app.core.config import settings
from app.core.errors import ValidationException

# Guard against decompression bomb attacks
Image.MAX_IMAGE_PIXELS = 10_000_000  # Max 10 Megapixels


@dataclass
class ValidatedImage:
    """Safely validated and re-encoded image container."""

    data: bytes
    format: str  # "PNG", "JPEG", "WEBP"
    mime_type: str  # "image/png", "image/jpeg", "image/webp"
    width: int
    height: int
    original_filename: str
    sanitized_filename: str


def sanitize_filename(filename: str | None) -> str:
    """Strips path traversal components and unsafe characters from filenames."""
    if not filename:
        return f"chart_{uuid.uuid4().hex[:8]}.png"
    base = os.path.basename(filename).strip()
    clean = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", base)
    if not clean or clean.startswith("."):
        clean = f"chart_{uuid.uuid4().hex[:8]}{clean}"
    return clean[:100]


def validate_and_process_chart_image(
    file_bytes: bytes,
    original_filename: str | None = None,
    content_type: str | None = None,
) -> ValidatedImage:
    """Performs rigorous security and format validation on uploaded chart image.

    Validates:
    1. Byte size within MAX_IMAGE_UPLOAD_SIZE_BYTES (default 10 MB).
    2. Decompression bomb protection via PIL MAX_IMAGE_PIXELS.
    3. Image format header (PNG, JPEG, WEBP).
    4. Image dimensions (width, height between 50px and MAX_IMAGE_DIMENSION_PX).
    5. Strips dangerous EXIF or embedded script payloads via safe re-encoding.
    """
    if not file_bytes:
        raise ValidationException("Uploaded chart image file is empty.")

    max_size = settings.MAX_IMAGE_UPLOAD_SIZE_BYTES
    if len(file_bytes) > max_size:
        max_mb = max_size / (1024 * 1024)
        raise ValidationException(
            f"Image file size ({len(file_bytes) / (1024 * 1024):.2f} MB) exceeds maximum allowed limit of {max_mb:.0f} MB."
        )

    clean_filename = sanitize_filename(original_filename)
    ext = os.path.splitext(clean_filename)[1].lower()

    if ext and ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationException(
            f"Unsupported image file extension '{ext}'. Allowed extensions: {settings.ALLOWED_IMAGE_EXTENSIONS}"
        )

    try:
        # Load image via Pillow and verify integrity
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()  # Verifies file integrity/magic bytes
    except Exception as exc:
        raise ValidationException(
            f"Malformed or invalid image file content. Could not decode image: {exc!s}"
        ) from exc

    # Re-open after verify() since PIL docs state verify() invalidates the image instance
    try:
        img = Image.open(io.BytesIO(file_bytes))
        detected_format = (img.format or "").upper()
        # Correct orientation based on EXIF if present
        img = ImageOps.exif_transpose(img)
    except Exception as exc:
        raise ValidationException(f"Failed to process image structure: {exc!s}") from exc

    if detected_format not in ["PNG", "JPEG", "WEBP"]:
        raise ValidationException(
            f"Unsupported image format '{detected_format}'. Only PNG, JPEG, and WEBP are supported."
        )

    width, height = img.size
    max_dim = settings.MAX_IMAGE_DIMENSION_PX

    if width < 50 or height < 50:
        raise ValidationException(
            f"Image dimensions ({width}x{height}) are too small for chart analysis. Minimum required is 50x50 pixels."
        )

    if width > max_dim or height > max_dim:
        raise ValidationException(
            f"Image dimensions ({width}x{height}) exceed maximum allowed dimension of {max_dim}x{max_dim} pixels."
        )

    # Safe re-encoding: Strips any malicious embedded EXIF/payloads and standardizes colorspace
    output_io = io.BytesIO()
    if detected_format == "PNG":
        # Preserve transparency if RGBA, otherwise RGB
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA" if "A" in img.mode else "RGB")
        img.save(output_io, format="PNG", optimize=True)
        out_format = "PNG"
        out_mime = "image/png"
    elif detected_format == "WEBP":
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA" if "A" in img.mode else "RGB")
        img.save(output_io, format="WEBP", quality=90)
        out_format = "WEBP"
        out_mime = "image/webp"
    else:  # JPEG
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.save(output_io, format="JPEG", quality=92, optimize=True)
        out_format = "JPEG"
        out_mime = "image/jpeg"

    re_encoded_bytes = output_io.getvalue()

    return ValidatedImage(
        data=re_encoded_bytes,
        format=out_format,
        mime_type=out_mime,
        width=width,
        height=height,
        original_filename=clean_filename,
        sanitized_filename=clean_filename,
    )
