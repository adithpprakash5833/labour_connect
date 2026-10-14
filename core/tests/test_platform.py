from accounts.models import User
from complaints.models import Complaint
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import get_template
from django.test import TestCase, override_settings
from django.urls import reverse
from jobs.models import Booking
from workers.models import WorkerDocument
from workers.search import search_workers

from core.models import ServiceCategory
from core.validators import validate_upload

from .helpers import PASSWORD, document, make_user, make_worker, service_data


class PlatformTests(TestCase):
    def setUp(self):
        self.customer = make_user("customer")
        self.worker = make_worker()
        self.admin = User.objects.create_superuser("admin", "admin@example.com", PASSWORD)

    def test_search_only_active_approved_workers(self):
        make_worker("pending", "PENDING", self.worker.category)
        make_worker("rejected", "REJECTED", self.worker.category)
        inactive = make_worker("inactive", category=self.worker.category)
        inactive.user.is_active = False
        inactive.user.save()
        response = self.client.get(reverse("find_workers") + "?q=Electrician")
        self.assertEqual(list(response.context["workers"]), [self.worker])
        self.assertEqual(
            self.client.get(reverse("worker_detail", args=[inactive.pk])).status_code, 404
        )

    def test_search_filters_sorting_distance_and_malformed_numbers(self):
        other = make_worker("otherworker", category=self.worker.category)
        other.service_rate = 200
        other.experience_years = 2
        other.save()
        self.worker.user.latitude = "9.9312"
        self.worker.user.longitude = "76.2673"
        self.worker.user.save()
        self.assertEqual(
            list(search_workers({"min_price": "300", "experience": "4"})), [self.worker]
        )
        self.assertEqual(list(search_workers({"sort": "price_low"}))[0], other)
        results = search_workers({"sort": "nearest", "latitude": "9.9312", "longitude": "76.2673"})
        self.assertEqual(results[0], self.worker)
        self.assertEqual(results[0].distance, 0)
        response = self.client.get(
            reverse("find_workers") + "?min_price=NaN&max_price=hello&rating=Infinity&latitude=999"
        )
        self.assertEqual(response.status_code, 200)

    def test_search_supports_full_names(self):
        self.worker.user.first_name = "Asha"
        self.worker.user.last_name = "Sample"
        self.worker.user.save()
        response = self.client.get(reverse("find_workers"), {"q": "Asha Sample"})
        self.assertEqual(list(response.context["workers"]), [self.worker])

    def test_documents_owner_admin_only_and_private_media_not_served(self):
        doc = WorkerDocument.objects.create(
            worker=self.worker, document_type="ID", document_file=document()
        )
        self.client.force_login(self.customer)
        self.assertEqual(
            self.client.get(reverse("document_download", args=[doc.pk])).status_code, 403
        )
        for user in (self.worker.user, self.admin):
            self.client.force_login(user)
            response = self.client.get(reverse("document_download", args=[doc.pk]))
            self.assertEqual(response.status_code, 200)
            self.assertIn("attachment", response["Content-Disposition"])
            self.assertTrue(b"".join(response.streaming_content).startswith(b"%PDF-"))
        self.assertEqual(self.client.get("/media/" + doc.document_file.name).status_code, 404)
        self.assertEqual(
            self.client.get("/private_media/" + doc.document_file.name).status_code, 404
        )

    def test_upload_extension_size_and_content(self):
        for file in [
            SimpleUploadedFile("bad.exe", b"bad"),
            SimpleUploadedFile("bad.pdf", b"<script>"),
            SimpleUploadedFile("bad.png", b"not image"),
            SimpleUploadedFile("large.pdf", b"%PDF-" + b"0" * (5 * 1024 * 1024)),
        ]:
            with self.assertRaises(ValidationError):
                validate_upload(file)

    def test_complaint_submission_response_notification_and_ownership(self):
        booking = Booking.objects.create(
            customer=self.customer, worker=self.worker, **service_data(self.worker.category)
        )
        self.client.force_login(self.customer)
        response = self.client.post(
            reverse("complaint_create"),
            {
                "subject": "Service issue",
                "description": "Please review this request.",
                "related_booking": booking.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        complaint = Complaint.objects.get(subject="Service issue")
        self.assertEqual(complaint.against_user, self.worker.user)
        self.assertTrue(self.admin.notifications.filter(notification_type="COMPLAINT").exists())
        self.client.force_login(self.worker.user)
        self.assertEqual(
            self.client.get(reverse("complaint_detail", args=[complaint.pk])).status_code, 404
        )
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.post(
                reverse("complaint_detail", args=[complaint.pk]),
                {"status": "RESOLVED", "admin_response": "We have resolved this."},
            ).status_code,
            302,
        )
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, "RESOLVED")
        self.assertTrue(
            self.customer.notifications.filter(notification_type="COMPLAINT_STATUS").exists()
        )

    def test_complaint_rejects_unrelated_service_and_resolution_without_response(self):
        other = make_user("other")
        booking = Booking.objects.create(
            customer=other, worker=self.worker, **service_data(self.worker.category)
        )
        self.client.force_login(self.customer)
        self.assertEqual(
            self.client.post(
                reverse("complaint_create"),
                {"subject": "Bad", "description": "Bad", "related_booking": booking.pk},
            ).status_code,
            200,
        )
        self.assertFalse(Complaint.objects.filter(subject="Bad").exists())
        complaint = Complaint.objects.create(
            created_by=self.customer, subject="Help", description="Help please"
        )
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("complaint_detail", args=[complaint.pk]),
            {"status": "RESOLVED", "admin_response": ""},
        )
        self.assertContains(response, "Include a response")

    def test_admin_category_management_and_activation(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("category_create"),
            {
                "name": "Repair",
                "slug": "repair",
                "description": "Repair work",
                "icon": "tools",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        category = ServiceCategory.objects.get(slug="repair")
        self.assertTrue(category.is_active)
        self.client.post(
            reverse("category_edit", args=[category.pk]),
            {"name": "Repair", "slug": "repair", "description": "Repair work", "icon": "tools"},
        )
        category.refresh_from_db()
        self.assertFalse(category.is_active)

    def test_admin_user_toggle_and_self_protection(self):
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.post(reverse("toggle_user", args=[self.customer.pk])).status_code, 302
        )
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_active)
        self.assertEqual(
            self.client.post(reverse("toggle_user", args=[self.admin.pk])).status_code, 403
        )

    def test_announcement_audience_and_rendering(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("announcements"),
            {
                "title": "Customer update",
                "message": "New services are available.",
                "audience": "CUSTOMER",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.customer.notifications.filter(title="Customer update").exists())
        self.assertFalse(self.worker.user.notifications.filter(title="Customer update").exists())
        self.assertContains(self.client.get(reverse("analytics")), "Platform analytics")

    def test_availability_and_document_upload(self):
        self.client.force_login(self.worker.user)
        self.assertEqual(
            self.client.post(reverse("availability"), {"availability_status": "BUSY"}).status_code,
            302,
        )
        self.worker.refresh_from_db()
        self.assertEqual(self.worker.availability_status, "BUSY")
        self.assertEqual(
            self.client.post(
                reverse("documents"), {"document_type": "SKILL", "document_file": document()}
            ).status_code,
            302,
        )
        self.assertTrue(self.worker.documents.filter(document_type="SKILL").exists())

    def test_all_templates_compile(self):
        for path in (settings.BASE_DIR / "templates").rglob("*.html"):
            get_template(str(path.relative_to(settings.BASE_DIR / "templates")).replace("\\", "/"))

    def test_public_and_role_pages_render(self):
        for name in (
            "home",
            "services",
            "about",
            "find_workers",
            "login",
            "register",
            "password_reset",
        ):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.assertEqual(
            self.client.get(reverse("worker_detail", args=[self.worker.pk])).status_code, 200
        )
        routes = {
            self.customer: [
                "customer_dashboard",
                "customer_jobs",
                "customer_bookings",
                "post_job",
                "profile",
                "settings",
                "payments",
                "reviews",
                "notifications",
                "complaints",
                "complaint_create",
                "password_change",
            ],
            self.worker.user: [
                "worker_dashboard",
                "worker_jobs",
                "worker_bookings",
                "available_jobs",
                "profile",
                "worker_profile",
                "availability",
                "documents",
                "settings",
                "payments",
                "reviews",
                "notifications",
                "complaints",
            ],
            self.admin: [
                "admin_dashboard",
                "admin_users",
                "admin_customers",
                "admin_workers",
                "admin_verifications",
                "admin_categories",
                "admin_jobs",
                "admin_bookings",
                "announcements",
                "analytics",
                "payments",
                "reviews",
                "complaints",
                "notifications",
                "settings",
            ],
        }
        for user, names in routes.items():
            self.client.force_login(user)
            for name in names:
                self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
            self.client.logout()

    @override_settings(DEBUG=False)
    def test_friendly_errors_and_escaped_user_content(self):
        self.assertContains(
            self.client.get("/unknown-page/"), "We couldn’t find that page", status_code=404
        )
        self.client.force_login(self.customer)
        self.assertContains(
            self.client.get(reverse("admin_dashboard")),
            "This page isn’t available",
            status_code=403,
        )
        self.worker.bio = "<script>alert(1)</script>"
        self.worker.save()
        response = self.client.get(reverse("worker_detail", args=[self.worker.pk]))
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "<script>alert(1)</script>")
