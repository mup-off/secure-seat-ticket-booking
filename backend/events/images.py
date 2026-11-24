"""Cover image uploads (plan, Phase 3: File uploads).

An upload is never stored as sent. It must be a real JPEG, PNG or WebP image within
the size limits. It is then decoded and re-encoded as a fresh JPEG, which:
- removes metadata such as GPS location from phone photos,
- removes anything hidden inside the file (e.g. a script disguised as an image),
- gives a known, safe file type served from our own origin.
Files get random names and live in MEDIA_ROOT, which is not served directly: the app
sends them through a view that checks who may see a draft's cover.
"""
import io

from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 40_000_000  # refuse "decompression bombs" (tiny files that expand hugely)
MAX_SIDE = 2000
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


class ImageRejected(Exception):
    pass


def clean_cover(uploaded_file):
    if uploaded_file.size > MAX_UPLOAD_BYTES:
        raise ImageRejected("The image must be 5 MB or smaller.")
    data = uploaded_file.read(MAX_UPLOAD_BYTES + 1)
    try:
        with Image.open(io.BytesIO(data)) as probe:
            fmt = probe.format
            width, height = probe.size
            probe.verify()  # checks the file structure without decoding everything
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise ImageRejected("That file is not a valid image. Use a JPEG, PNG or WebP picture.")
    if fmt not in ALLOWED_FORMATS:
        raise ImageRejected("Use a JPEG, PNG or WebP picture.")
    if width * height > MAX_PIXELS:
        raise ImageRejected("The image is too large. Use one under 40 megapixels.")

    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    with Image.open(io.BytesIO(data)) as img:
        img.load()
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        else:
            img = img.convert("RGB")
        img.thumbnail((MAX_SIDE, MAX_SIDE))
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=85, optimize=True)  # no EXIF copied
    return ContentFile(out.getvalue(), name="cover.jpg")
