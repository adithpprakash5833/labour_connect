from core.storage import photo_path
from core.validators import validate_phone, validate_photo
from django.contrib.auth.models import AbstractUser, UserManager
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Lower


class PlatformUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields["role"] = "ADMINISTRATOR"
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        WORKER = "WORKER", "Worker"
        ADMINISTRATOR = "ADMINISTRATOR", "Administrator"

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=22, validators=[validate_phone])
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.CUSTOMER, db_index=True
    )
    profile_photo = models.ImageField(upload_to=photo_path, blank=True, validators=[validate_photo])
    address = models.CharField(max_length=300, blank=True)
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
    objects = PlatformUserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="unique_email_case_insensitive")
        ]

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    @property
    def initials(self):
        return "".join(part[0] for part in self.display_name.split()[:2]).upper()

    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        if self.is_superuser:
            self.role = self.Role.ADMINISTRATOR
        super().save(*args, **kwargs)
