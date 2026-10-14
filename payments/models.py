from decimal import Decimal

from core.models import TimeStampedModel
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Payment(TimeStampedModel):
    class Method(models.TextChoices):
        CASH = "CASH", "Cash — worker confirms receipt"
        UPI = "UPI", "UPI — worker confirms receipt"
        DEMO = "DEMO", "Demo online — simulation only"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Awaiting receipt confirmation"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payments"
    )
    worker = models.ForeignKey(
        "workers.WorkerProfile", on_delete=models.PROTECT, related_name="payments"
    )
    booking = models.OneToOneField(
        "jobs.Booking", null=True, blank=True, on_delete=models.PROTECT, related_name="payment"
    )
    job = models.OneToOneField(
        "jobs.Job", null=True, blank=True, on_delete=models.PROTECT, related_name="payment"
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("1"))]
    )
    payment_method = models.CharField(max_length=5, choices=Method.choices)
    transaction_reference = models.CharField(max_length=150, blank=True)
    payment_status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    payment_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(booking__isnull=False, job__isnull=True)
                    | models.Q(booking__isnull=True, job__isnull=False)
                ),
                name="payment_exactly_one_service",
            )
        ]

    @property
    def service(self):
        return self.booking or self.job
