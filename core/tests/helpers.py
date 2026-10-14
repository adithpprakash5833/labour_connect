import io
from datetime import time, timedelta
from decimal import Decimal

from accounts.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image
from workers.models import WorkerProfile

from core.models import ServiceCategory

PASSWORD = "Test-Only-Secure!591"


def photo():
    buffer = io.BytesIO()
    Image.new("RGB", (20, 20), "blue").save(buffer, "PNG")
    return SimpleUploadedFile("portrait.png", buffer.getvalue(), content_type="image/png")


def document():
    return SimpleUploadedFile(
        "id.pdf", b"%PDF-1.4\nfictional-test-document", content_type="application/pdf"
    )


def make_user(username, role="CUSTOMER"):
    return User.objects.create_user(
        username,
        f"{username}@example.com",
        PASSWORD,
        role=role,
        first_name=username.title(),
        last_name="Test",
        phone="+919800000001",
        address="Kochi",
    )


def make_worker(username="worker", status="APPROVED", category=None):
    category = (
        category or ServiceCategory.objects.get_or_create(name="Electrician", slug="electrician")[0]
    )
    user = make_user(username, "WORKER")
    return WorkerProfile.objects.create(
        user=user,
        category=category,
        designation="Electrician",
        skills="Wiring, repairs",
        experience_years=5,
        service_rate=Decimal("500"),
        working_area="Kochi",
        bio="Experienced local electrician.",
        verification_status=status,
    )


def service_data(category):
    return {
        "category": category,
        "title": "Electrical repair",
        "description": "Repair the living room wiring safely.",
        "budget": Decimal("1500"),
        "job_date": timezone.localdate() + timedelta(days=3),
        "preferred_time": time(10, 0),
        "address": "Kochi",
    }


def registration_data(role="CUSTOMER", category=None):
    data = {
        "role": role,
        "first_name": "New",
        "last_name": "Person",
        "username": "new_person",
        "email": "new@example.com",
        "phone": "+919800000002",
        "password1": PASSWORD,
        "password2": PASSWORD,
        "address": "Kochi",
    }
    if role == "WORKER":
        data.update(
            {
                "designation": "Electrician",
                "category": category.pk,
                "skills": "Wiring",
                "experience_years": 3,
                "service_rate": "400",
                "working_area": "Kochi",
                "availability_status": "AVAILABLE",
                "bio": "Local electrician profile.",
                "profile_photo": photo(),
                "identity_document": document(),
            }
        )
    return data
