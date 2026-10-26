"""Validate and normalise uploaded plant photos before they are stored in the database."""
import warnings
from io import BytesIO

from django.core.exceptions import ValidationError
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_SIDE = 1600
ALLOWED_FORMATS = {'JPEG', 'PNG', 'WEBP'}
ACCEPT = 'image/jpeg,image/png,image/webp'
Image.MAX_IMAGE_PIXELS = 40_000_000


def process_photo(upload):
    """Return (jpeg_bytes, width, height).

    Checks size and real file type (not just the extension), applies the EXIF
    rotation, strips all metadata (including GPS location), downsizes to at most
    1600 px and re-encodes as JPEG so every stored photo is small and safe to serve.
    """
    if upload.size > MAX_UPLOAD_BYTES:
        raise ValidationError('The photo must be 5 MB or smaller.', code='too_large')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            upload.seek(0)
            with Image.open(upload) as probe:
                image_format = probe.format
                probe.verify()
            upload.seek(0)
            image = Image.open(upload)
            image.load()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError,
            Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValidationError('Upload a valid JPG, PNG or WebP image.', code='invalid') from exc
    if image_format not in ALLOWED_FORMATS:
        raise ValidationError('Upload a JPG, PNG or WebP image.', code='format')

    image = ImageOps.exif_transpose(image)
    if image.mode in ('RGBA', 'LA', 'P'):
        image = image.convert('RGBA')
        background = Image.new('RGB', image.size, (255, 253, 245))
        background.paste(image, mask=image.getchannel('A'))
        image = background
    elif image.mode != 'RGB':
        image = image.convert('RGB')
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    out = BytesIO()
    image.save(out, 'JPEG', quality=82, optimize=True, progressive=True)
    return out.getvalue(), image.width, image.height
