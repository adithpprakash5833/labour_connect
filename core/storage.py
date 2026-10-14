import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(location=settings.PRIVATE_MEDIA_ROOT)

    def url(self, name):
        raise ValueError("Private documents require an authenticated download view.")


def document_path(instance, filename):
    return (
        f"worker_documents/{instance.worker_id}/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"
    )


def photo_path(instance, filename):
    return f"profile_images/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"
