import re
from pathlib import Path

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


def validate_phone(value):
    if (
        not re.fullmatch(r"\+?[0-9][0-9 ()-]{7,18}", value)
        or not 8 <= len(re.sub(r"\D", "", value)) <= 15
    ):
        raise ValidationError("Enter a valid phone number with 8–15 digits.")


def validate_upload(file):
    """Check size, extension, and content; filenames alone are not trusted."""
    if file.size > 5 * 1024 * 1024:
        raise ValidationError("Files must be no larger than 5 MB.")
    extension = Path(file.name).suffix.lower()
    if extension not in (".pdf", ".png", ".jpg", ".jpeg"):
        raise ValidationError("Upload a PDF, PNG or JPEG file.")
    file.seek(0)
    if extension == ".pdf":
        if file.read(5) != b"%PDF-":
            raise ValidationError("This file is not a valid PDF.")
    else:
        try:
            img = Image.open(file)
            if img.format not in ("PNG", "JPEG"):
                raise ValidationError("Upload a PNG or JPEG image.")
            img.verify()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise ValidationError("This image is invalid or too large.") from exc
    file.seek(0)


def validate_photo(file):
    if Path(file.name).suffix.lower() not in (".png", ".jpg", ".jpeg"):
        raise ValidationError("Profile photos must be PNG or JPEG.")
    validate_upload(file)
