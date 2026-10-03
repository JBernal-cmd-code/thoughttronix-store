"""Product image processing — the one door every product image comes through.

Employees' uploads (the back-office form and the Django admin) and the
``seed`` command all call :func:`prepare_product_image`. It validates the
file, crops it to the catalog's 4:5 portrait frame, resizes it to
800×1000, and encodes it as WebP. Only the processed file is ever stored,
so every image in the catalog has the same shape, size, and format.

A file the site can't use raises ``ValidationError`` with a plain-language
message saying what's wrong and what to do instead.
"""

import warnings
from io import BytesIO
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
FRAME_SIZE = (800, 1000)  # 4:5 portrait, width × height
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
WEBP_QUALITY = 80

# ISO base-media brands used by HEIC/HEIF photos (iPhones, many Androids).
HEIF_BRANDS = {b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"mif1", b"msf1"}

SUPPORTED = "Upload a JPEG, PNG, or WebP image instead."


def prepare_product_image(uploaded_file: File) -> ContentFile:
    """Validate an image file and return it processed for the catalog.

    The result is an 800×1000 WebP, center-cropped from the original to
    the 4:5 frame (never letterboxed), with the camera's orientation
    applied and any transparency kept. Assign it to ``Product.image``;
    the field's ``upload_to`` gives it a unique filename.

    Raises ``ValidationError`` when the file is over 10 MB, can't be
    decoded, isn't a JPEG, PNG, or WebP, or is smaller than 800×1000
    once cropped to 4:5.
    """
    filename = Path(uploaded_file.name or "image").name

    if uploaded_file.size > MAX_UPLOAD_BYTES:
        raise ValidationError(
            f"“{filename}” is {uploaded_file.size / (1024 * 1024):.1f} MB. "
            "Images must be 10 MB or smaller — try exporting it as a JPEG.",
            code="too_large",
        )

    uploaded_file.seek(0)
    head = uploaded_file.read(512)
    uploaded_file.seek(0)

    try:
        # Pillow only warns about images just over its pixel limit; an
        # image that large is treated as unreadable, like one over it.
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(uploaded_file)
            image_format = image.format
            image.load()
    except UnidentifiedImageError:
        raise _unidentified(filename, head) from None
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        SyntaxError,
        ValueError,
    ):
        raise ValidationError(
            f"We couldn't read “{filename}” as an image. It may be damaged "
            f"or incomplete. {SUPPORTED}",
            code="unreadable",
        ) from None

    if image_format not in ALLOWED_FORMATS:
        raise ValidationError(
            f"“{filename}” is a {image_format} image, which the catalog "
            f"doesn't support. {SUPPORTED}",
            code="unsupported_format",
        )

    icc_profile = image.info.get("icc_profile")
    image = ImageOps.exif_transpose(image)

    width, height = image.size
    crop_width, crop_height = _crop_size(width, height)
    min_width, min_height = FRAME_SIZE
    if crop_width < min_width or crop_height < min_height:
        raise ValidationError(
            f"“{filename}” is {width}×{height} pixels. Cropped to the 4:5 "
            f"product frame that's {crop_width}×{crop_height}, smaller than "
            f"the {min_width}×{min_height} minimum. Upload a larger image.",
            code="too_small",
        )

    has_alpha = image.mode in ("RGBA", "LA", "PA") or (
        image.mode == "P" and "transparency" in image.info
    )
    image = image.convert("RGBA" if has_alpha else "RGB")
    image = ImageOps.fit(
        image, FRAME_SIZE, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5)
    )

    buffer = BytesIO()
    image.save(buffer, "WEBP", quality=WEBP_QUALITY, icc_profile=icc_profile)
    return ContentFile(buffer.getvalue(), name="product.webp")


def _crop_size(width: int, height: int) -> tuple[int, int]:
    """The largest 4:5 rectangle that fits inside ``width`` × ``height``."""
    if width * 5 > height * 4:  # wider than 4:5 — trim the sides
        return height * 4 // 5, height
    return width, width * 5 // 4  # taller than 4:5 — trim top and bottom


def _unidentified(filename: str, head: bytes) -> ValidationError:
    """The rejection for a file Pillow can't recognize at all, with a
    format-specific hint for the two such files people most often try."""
    suffix = Path(filename).suffix.lower()
    if suffix in (".heic", ".heif") or (
        head[4:8] == b"ftyp" and head[8:12] in HEIF_BRANDS
    ):
        return ValidationError(
            f"“{filename}” is a HEIC photo, which web browsers can't show. "
            "Export it as a JPEG (most photo apps offer this under Export or "
            "Share) and upload that instead.",
            code="heic",
        )
    if suffix == ".svg" or b"<svg" in head.lower():
        return ValidationError(
            f"“{filename}” is an SVG drawing. Product images must be photos. "
            f"{SUPPORTED}",
            code="unsupported_format",
        )
    return ValidationError(
        f"We couldn't read “{filename}” as an image. It may be damaged, or "
        f"not an image at all. {SUPPORTED}",
        code="unreadable",
    )
