from decimal import Decimal

from core.models import TimeStampedModel
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class ServiceStatus(models.TextChoices):
    REQUESTED = "REQUESTED", "Requested"
    ACCEPTED = "ACCEPTED", "Accepted"
    REJECTED = "REJECTED", "Rejected"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"
    OPEN = "OPEN", "Open"


class Service(TimeStampedModel):
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="%(class)s_services"
    )
    category = models.ForeignKey(
        "core.ServiceCategory", on_delete=models.PROTECT, related_name="%(class)s_services"
    )
    title = models.CharField(max_length=160)
    description = models.TextField(max_length=4000)
    budget = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("1"))]
    )
    job_date = models.DateField()
    preferred_time = models.TimeField()
    address = models.CharField(max_length=300)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    urgent = models.BooleanField(default=False)
    status = models.CharField(max_length=12, choices=ServiceStatus.choices, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def kind(self):
        return "booking" if isinstance(self, Booking) else "job"


class Booking(Service):
    worker = models.ForeignKey(
        "workers.WorkerProfile", on_delete=models.PROTECT, related_name="bookings"
    )
    status = models.CharField(
        max_length=12,
        choices=[c for c in ServiceStatus.choices if c[0] != "OPEN"],
        default=ServiceStatus.REQUESTED,
        db_index=True,
    )
    special_instructions = models.TextField(max_length=2000, blank=True)


class Job(Service):
    worker = models.ForeignKey(
        "workers.WorkerProfile",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="jobs",
    )
    required_skill = models.CharField(max_length=200)
    status = models.CharField(
        max_length=12,
        choices=[c for c in ServiceStatus.choices if c[0] not in ("REQUESTED", "REJECTED")],
        default=ServiceStatus.OPEN,
        db_index=True,
    )

    class Meta(Service.Meta):
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(status="OPEN", worker__isnull=True)
                    | models.Q(status="CANCELLED")
                    | models.Q(
                        status__in=["ACCEPTED", "IN_PROGRESS", "COMPLETED"], worker__isnull=False
                    )
                ),
                name="job_assignment_matches_status",
            )
        ]
