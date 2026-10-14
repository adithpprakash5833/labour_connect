from core.models import TimeStampedModel
from django.conf import settings
from django.db import models


class Complaint(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_REVIEW = "IN_REVIEW", "In review"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="complaints"
    )
    against_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="complaints_against",
    )
    related_job = models.ForeignKey("jobs.Job", null=True, blank=True, on_delete=models.PROTECT)
    related_booking = models.ForeignKey(
        "jobs.Booking", null=True, blank=True, on_delete=models.PROTECT
    )
    subject = models.CharField(max_length=160)
    description = models.TextField(max_length=4000)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    admin_response = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(related_job__isnull=True)
                | models.Q(related_booking__isnull=True),
                name="complaint_at_most_one_service",
            )
        ]
