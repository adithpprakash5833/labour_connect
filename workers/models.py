from decimal import Decimal

from core.models import TimeStampedModel
from core.storage import PrivateStorage, document_path
from core.validators import validate_upload
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg


class WorkerProfile(TimeStampedModel):
    class Verification(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    class Availability(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        BUSY = "BUSY", "Busy"
        UNAVAILABLE = "UNAVAILABLE", "Unavailable"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="worker_profile"
    )
    designation = models.CharField(max_length=100)
    category = models.ForeignKey(
        "core.ServiceCategory", on_delete=models.PROTECT, related_name="workers"
    )
    skills = models.CharField(max_length=400)
    experience_years = models.PositiveSmallIntegerField(
        default=0, validators=[MaxValueValidator(70)]
    )
    service_rate = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("1"))]
    )
    availability_status = models.CharField(
        max_length=12, choices=Availability.choices, default=Availability.AVAILABLE, db_index=True
    )
    working_area = models.CharField(max_length=160)
    bio = models.TextField(max_length=2000)
    verification_status = models.CharField(
        max_length=10, choices=Verification.choices, default=Verification.PENDING, db_index=True
    )
    verification_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.user.display_name

    @property
    def average_rating(self):
        return self.reviews.aggregate(value=Avg("rating"))["value"] or 0

    @property
    def total_reviews(self):
        return self.reviews.count()

    @property
    def total_completed_jobs(self):
        return (
            self.jobs.filter(status="COMPLETED").count()
            + self.bookings.filter(status="COMPLETED").count()
        )


class WorkerDocument(models.Model):
    class Type(models.TextChoices):
        ID = "ID", "ID proof"
        ADDRESS = "ADDRESS", "Address proof"
        SKILL = "SKILL", "Skill certificate"
        PROFESSIONAL = "PROFESSIONAL", "Professional certificate"
        OTHER = "OTHER", "Other"

    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=15, choices=Type.choices)
    document_file = models.FileField(
        storage=PrivateStorage(), upload_to=document_path, validators=[validate_upload]
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verification_status = models.CharField(
        max_length=10, choices=WorkerProfile.Verification.choices, default="PENDING"
    )
    admin_note = models.TextField(blank=True)


class VerificationEvent(models.Model):
    worker = models.ForeignKey(
        WorkerProfile, on_delete=models.CASCADE, related_name="verification_history"
    )
    administrator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    status = models.CharField(max_length=10, choices=WorkerProfile.Verification.choices)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
