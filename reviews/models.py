from core.models import TimeStampedModel
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Review(TimeStampedModel):
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reviews"
    )
    worker = models.ForeignKey(
        "workers.WorkerProfile", on_delete=models.PROTECT, related_name="reviews"
    )
    booking = models.OneToOneField(
        "jobs.Booking", null=True, blank=True, on_delete=models.PROTECT, related_name="review"
    )
    job = models.OneToOneField(
        "jobs.Job", null=True, blank=True, on_delete=models.PROTECT, related_name="review"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    text = models.TextField(max_length=2000)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(booking__isnull=False, job__isnull=True)
                    | models.Q(booking__isnull=True, job__isnull=False)
                ),
                name="review_exactly_one_service",
            ),
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5), name="review_rating_range"
            ),
        ]

    @property
    def service(self):
        return self.booking or self.job
