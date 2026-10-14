from django.db import models

from core.validators import validate_photo


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ServiceCategory(TimeStampedModel):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=60, default="tools")
    image = models.ImageField(upload_to="categories/", blank=True, validators=[validate_photo])
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
