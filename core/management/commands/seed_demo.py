import io
import secrets
from datetime import time, timedelta
from decimal import Decimal

from accounts.models import User
from adminpanel.models import Announcement
from complaints.models import Complaint
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from jobs.models import Booking, Job
from notifications.services import notify
from payments.models import Payment
from PIL import Image, ImageDraw
from reviews.models import Review
from workers.models import VerificationEvent, WorkerDocument, WorkerProfile

from core.models import ServiceCategory


class Command(BaseCommand):
    help = "Seed clearly fictional demonstration records and generate random demo passwords."

    @transaction.atomic
    def handle(self, *args, **options):
        call_command("seed_categories", verbosity=0)
        credentials = []

        def account(username, role, first, last):
            user = User.objects.filter(username=username).first()
            if user:
                return user
            password = secrets.token_urlsafe(14)
            values = {
                "first_name": first,
                "last_name": last,
                "role": role,
                "phone": "+919900000001",
                "address": "Fictional sample address, Kochi",
                "latitude": "9.931200",
                "longitude": "76.267300",
            }
            manager = (
                User.objects.create_superuser
                if role == "ADMINISTRATOR"
                else User.objects.create_user
            )
            user = manager(username, f"{username}@example.com", password, **values)
            credentials.append(f"{username} ({role}) | {password}")
            image = Image.new(
                "RGB",
                (240, 240),
                ["#E4E8FF", "#F8EACF", "#DCF0E7", "#F0E1F7"][len(credentials) % 4],
            )
            draw = ImageDraw.Draw(image)
            # Original geometric demo avatar; no remote images or real identity material.
            draw.ellipse((80, 45, 160, 125), fill="#B78568")
            draw.rounded_rectangle(
                (48, 140, 192, 255),
                radius=60,
                fill=["#5264B5", "#71957E", "#B78B57"][len(credentials) % 3],
            )
            draw.arc((80, 35, 160, 109), 180, 360, fill="#333C56", width=25)
            buffer = io.BytesIO()
            image.save(buffer, "PNG")
            user.profile_photo.save(f"{username}.png", ContentFile(buffer.getvalue()), save=True)
            return user

        admin = account("demo_admin", "ADMINISTRATOR", "Alex", "Administrator")
        customers = [
            account(f"demo_customer{i + 1}", "CUSTOMER", first, "Sample")
            for i, first in enumerate(["Maya", "Nikhil", "Asha"])
        ]
        profiles = []
        names = [
            "Arun",
            "Devika",
            "Rahul",
            "Meera",
            "Sanjay",
            "Farah",
            "Vivek",
            "Anjali",
            "Joseph",
            "Priya",
            "Rohan",
            "Leela",
            "Anil",
        ]
        cats = [
            "Electrician",
            "Plumber",
            "Carpenter",
            "Painter",
            "Electrician",
            "Cleaner",
            "AC Technician",
            "Gardener",
            "Mechanic",
            "Home Maintenance Worker",
            "Welder",
            "Mason",
            "Driver",
        ]
        for i, (name, category_name) in enumerate(zip(names, cats)):
            user = account(f"demo_worker{i + 1}", "WORKER", name, "Sample")
            category = ServiceCategory.objects.get(name=category_name)
            state = "APPROVED" if i < 10 else "PENDING" if i < 12 else "REJECTED"
            worker, created = WorkerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "designation": f"{category_name} specialist",
                    "category": category,
                    "skills": f"{category_name}, maintenance, installations",
                    "experience_years": 3 + i % 8,
                    "service_rate": Decimal(250 + 50 * (i % 6)),
                    "working_area": [
                        "Kochi",
                        "Edappally, Kochi",
                        "Kakkanad, Kochi",
                        "Aluva, Kochi",
                    ][i % 4],
                    "bio": f"Fictional demonstration profile. {name} offers {category_name.lower()} services with care, clear communication and attention to detail.",
                    "verification_status": state,
                    "verification_reason": "Sample rejection: the submitted demo document needs clarification."
                    if state == "REJECTED"
                    else "",
                },
            )
            if created:
                document = Image.new("RGB", (900, 450), "#F3F4FA")
                drawing = ImageDraw.Draw(document)
                drawing.text(
                    (45, 45), "FICTIONAL DEMO DOCUMENT - NOT VALID ID", fill="#C44A59", font_size=27
                )
                drawing.text(
                    (45, 125),
                    f"{user.display_name} / sample worker verification",
                    fill="#303B64",
                    font_size=23,
                )
                drawing.text(
                    (45, 205),
                    "This file exists only to demonstrate protected document downloads.",
                    fill="#667190",
                    font_size=19,
                )
                buffer = io.BytesIO()
                document.save(buffer, "PNG")
                WorkerDocument.objects.create(
                    worker=worker,
                    document_type="ID",
                    document_file=ContentFile(buffer.getvalue(), name="fictional-demo.png"),
                    verification_status=state,
                )
                if state != "PENDING":
                    VerificationEvent.objects.create(
                        worker=worker,
                        administrator=admin,
                        status=state,
                        reason="Fictional demo decision.",
                    )
            profiles.append(worker)
        today = timezone.localdate()
        for i, worker in enumerate(profiles[:10]):
            customer = customers[i % 3]
            for back in range(4):
                title = f"[Demo] {worker.category.name} service {back + 1} / {i + 1}"
                service, created = Booking.objects.get_or_create(
                    title=title,
                    customer=customer,
                    defaults={
                        "worker": worker,
                        "category": worker.category,
                        "description": "Fictional completed service for the MCA demonstration.",
                        "budget": worker.service_rate * 3,
                        "job_date": today - timedelta(days=back * 28 + 2),
                        "preferred_time": time(10, 0),
                        "address": "Fictional sample address, Kochi",
                        "status": "COMPLETED",
                    },
                )
                if created:
                    created_at = timezone.now() - timedelta(days=back * 28 + 2)
                    Booking.objects.filter(pk=service.pk).update(
                        created_at=created_at, completed_at=created_at
                    )
                    payment = Payment.objects.create(
                        customer=customer,
                        worker=worker,
                        booking=service,
                        amount=service.budget,
                        payment_method="DEMO",
                        payment_status="PAID",
                        transaction_reference=f"DEMO-SEED-{service.pk}",
                        payment_date=created_at,
                    )
                    Payment.objects.filter(pk=payment.pk).update(created_at=created_at)
                    Review.objects.create(
                        customer=customer,
                        worker=worker,
                        booking=service,
                        rating=5 if (i + back) % 3 else 4,
                        text="Sample demo review: clear communication and careful work. This is fictional seed content.",
                    )
            requested, created = Booking.objects.get_or_create(
                title=f"[Demo] Upcoming {worker.category.name.lower()} request",
                customer=customer,
                defaults={
                    "worker": worker,
                    "category": worker.category,
                    "description": "Please help with a local service task. Fictional demo request.",
                    "budget": worker.service_rate * 2,
                    "job_date": today + timedelta(days=3),
                    "preferred_time": time(9, 30),
                    "address": "Fictional sample address, Kochi",
                    "status": "REQUESTED",
                },
            )
            if created:
                notify(
                    worker.user,
                    "BOOKING_REQUEST",
                    "Sample booking request",
                    requested.title,
                    requested.pk,
                )
                if not customer.notifications.filter(notification_type="WELCOME").exists():
                    notify(
                        customer,
                        "WELCOME",
                        "Welcome to your demo workspace",
                        "All demo people, documents, jobs and reviews are fictional.",
                    )
        for i, category in enumerate(ServiceCategory.objects.filter(is_active=True)[:8]):
            Job.objects.get_or_create(
                title=f"[Demo] Local {category.name.lower()} opportunity",
                customer=customers[i % 3],
                defaults={
                    "category": category,
                    "required_skill": category.name,
                    "description": "Fictional open job. Discuss the scope before accepting.",
                    "budget": 800 + i * 150,
                    "job_date": today + timedelta(days=4 + i),
                    "preferred_time": time(11, 0),
                    "address": "Fictional sample address, Kakkanad, Kochi",
                    "urgent": i % 3 == 0,
                    "status": "OPEN",
                },
            )
        Complaint.objects.get_or_create(
            created_by=customers[0],
            subject="[Demo] Clarification about a scheduled service",
            defaults={"description": "Fictional complaint for demonstrating the support workflow."},
        )
        Announcement.objects.get_or_create(
            title="Welcome to the fictional demo",
            defaults={
                "message": "All seeded accounts, profiles, reviews and payment records are sample content. Demo online payments do not transfer money.",
                "audience": "ALL",
                "created_by": admin,
            },
        )
        if credentials:
            credential_path = settings.BASE_DIR / "demo_accounts.txt"
            with credential_path.open("a", encoding="utf-8") as file:
                file.write(
                    "FICTIONAL DEMO ACCOUNTS — generated random passwords. Keep this local.\n"
                    + "\n".join(credentials)
                    + "\n"
                )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Demo data created. Random passwords saved to {credential_path.name}."
                )
            )
        else:
            self.stdout.write("Demo records already exist; passwords were not changed.")
