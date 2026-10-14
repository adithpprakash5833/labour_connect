from core.models import TimeStampedModel
from django.conf import settings
from django.db import models


class Announcement(TimeStampedModel):
    title = models.CharField(max_length=160)
    message = models.TextField(max_length=3000)
    audience = models.CharField(
        max_length=10,
        choices=[("ALL", "Everyone"), ("CUSTOMER", "Customers"), ("WORKER", "Workers")],
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        ordering = ["-created_at"]
