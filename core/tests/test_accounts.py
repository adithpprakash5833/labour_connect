from accounts.models import User
from adminpanel.services import verify_worker
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from core.models import ServiceCategory

from .helpers import PASSWORD, make_user, make_worker, registration_data


class AccountTests(TestCase):
    def setUp(self):
        cache.clear()
        self.category = ServiceCategory.objects.create(name="Electrician", slug="electrician")
        self.admin = User.objects.create_superuser("admin", "admin@example.com", PASSWORD)

    def test_customer_registration(self):
        response = self.client.post(reverse("register"), registration_data())
        self.assertRedirects(response, reverse("login"))
        user = User.objects.get(username="new_person")
        self.assertEqual(user.role, "CUSTOMER")
        self.assertTrue(user.check_password(PASSWORD))

    def test_worker_registration_starts_pending_with_private_document(self):
        response = self.client.post(reverse("register"), registration_data("WORKER", self.category))
        self.assertRedirects(response, reverse("login"))
        worker = User.objects.get(username="new_person").worker_profile
        self.assertEqual(worker.verification_status, "PENDING")
        self.assertEqual(worker.documents.count(), 1)
        with self.assertRaises(ValueError):
            worker.documents.first().document_file.url

    def test_public_admin_registration_is_rejected(self):
        data = registration_data("ADMINISTRATOR")
        self.assertEqual(self.client.post(reverse("register"), data).status_code, 200)
        self.assertFalse(User.objects.filter(username="new_person").exists())

    def test_duplicate_email_case_and_username_validation(self):
        make_user("new_person")
        data = registration_data()
        data["email"] = "NEW_PERSON@EXAMPLE.COM"
        response = self.client.post(reverse("register"), data)
        self.assertContains(response, "already exists")
        self.assertEqual(User.objects.filter(username="new_person").count(), 1)

    def test_password_phone_location_and_missing_worker_fields_validation(self):
        data = registration_data()
        data.update(password2="wrong", phone="abc", latitude="999")
        response = self.client.post(reverse("register"), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="new_person").exists())
        data = registration_data("WORKER", self.category)
        del data["identity_document"]
        response = self.client.post(reverse("register"), data)
        self.assertContains(response, "required for workers")

    def test_pending_worker_no_session_and_direct_urls_blocked(self):
        worker = make_worker("pending", "PENDING", self.category)
        response = self.client.post(
            reverse("login"), {"username": worker.user.username, "password": PASSWORD}
        )
        self.assertContains(response, "awaiting administrator verification")
        self.assertNotIn("_auth_user_id", self.client.session)
        self.client.force_login(worker.user)
        for url in (
            "worker_dashboard",
            "worker_jobs",
            "worker_profile",
            "documents",
            "payments",
            "notifications",
        ):
            self.assertEqual(self.client.get(reverse(url)).status_code, 403, url)

    def test_approval_allows_login_and_notifies(self):
        worker = make_worker("pending", "PENDING", self.category)
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("verify_worker", args=[worker.pk]),
            {"status": "APPROVED", "reason": "Identity checked"},
        )
        self.assertEqual(response.status_code, 302)
        worker.refresh_from_db()
        self.assertEqual(worker.verification_status, "APPROVED")
        self.assertEqual(worker.verification_history.count(), 1)
        self.assertTrue(worker.user.notifications.filter(notification_type="VERIFICATION").exists())
        self.client.logout()
        response = self.client.post(
            reverse("login"), {"username": worker.user.username, "password": PASSWORD}
        )
        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse("worker_dashboard")).status_code, 200)

    def test_rejected_worker_login_blocked_with_reason(self):
        worker = make_worker("rejected", "REJECTED", self.category)
        worker.verification_reason = "Unreadable identity"
        worker.save()
        response = self.client.post(
            reverse("login"), {"username": "rejected", "password": PASSWORD}
        )
        self.assertContains(response, "Unreadable identity")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_admin_requires_rejection_reason(self):
        worker = make_worker("pending", "PENDING", self.category)
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("verify_worker", args=[worker.pk]), {"status": "REJECTED", "reason": ""}
        )
        self.assertContains(response, "rejection reason is required")
        worker.refresh_from_db()
        self.assertEqual(worker.verification_status, "PENDING")

    def test_role_url_isolation_and_admin_role(self):
        self.assertEqual(self.admin.role, "ADMINISTRATOR")
        customer = make_user("customer")
        worker = make_worker(category=self.category)
        self.client.force_login(customer)
        for name in ("worker_dashboard", "admin_dashboard", "admin_verifications", "documents"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 403)
        self.client.force_login(worker.user)
        for name in ("customer_dashboard", "post_job", "admin_dashboard"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("admin_dashboard")).status_code, 200)

    def test_profile_cannot_change_role(self):
        user = make_user("customer")
        self.client.force_login(user)
        self.client.post(
            reverse("profile"),
            {
                "first_name": "Updated",
                "last_name": "Test",
                "phone": "+919800000001",
                "address": "Kochi",
                "role": "ADMINISTRATOR",
            },
        )
        user.refresh_from_db()
        self.assertEqual(user.role, "CUSTOMER")
        self.assertEqual(user.first_name, "Updated")

    def test_deactivation_revokes_existing_session(self):
        customer = make_user("customer")
        self.client.force_login(customer)
        customer.is_active = False
        customer.save()
        self.assertEqual(self.client.get(reverse("customer_dashboard")).status_code, 302)

    def test_revoked_verification_blocks_existing_session(self):
        worker = make_worker(category=self.category)
        self.client.force_login(worker.user)
        verify_worker(worker.pk, self.admin, "REJECTED", "Recheck needed")
        self.assertEqual(self.client.get(reverse("worker_dashboard")).status_code, 403)

    def test_csrf_required_for_mutations_and_logout_is_post(self):
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        secure = Client(enforce_csrf_checks=True)
        self.assertEqual(secure.post(reverse("register"), registration_data()).status_code, 403)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_email_and_password_change(self):
        customer = make_user("customer")
        self.assertEqual(
            self.client.post(reverse("password_reset"), {"email": customer.email}).status_code, 302
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/accounts/password/reset/", mail.outbox[0].body)
        self.client.force_login(customer)
        response = self.client.post(
            reverse("password_change"),
            {
                "old_password": PASSWORD,
                "new_password1": "Changed-Safely!826",
                "new_password2": "Changed-Safely!826",
            },
        )
        self.assertEqual(response.status_code, 302)
        customer.refresh_from_db()
        self.assertTrue(customer.check_password("Changed-Safely!826"))

    def test_password_reset_token_completes(self):
        customer = make_user("customer")
        token = default_token_generator.make_token(customer)
        uid = urlsafe_base64_encode(force_bytes(customer.pk))
        response = self.client.get(reverse("password_reset_confirm", args=[uid, token]))
        self.assertEqual(response.status_code, 302)
        response = self.client.post(
            response.url, {"new_password1": "Reset-Safely!739", "new_password2": "Reset-Safely!739"}
        )
        self.assertEqual(response.status_code, 302)
        customer.refresh_from_db()
        self.assertTrue(customer.check_password("Reset-Safely!739"))

    @override_settings(
        SEND_NOTIFICATION_EMAIL=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
    )
    def test_verification_email_is_sent_after_commit(self):
        worker = make_worker("pending", "PENDING", self.category)
        with self.captureOnCommitCallbacks(execute=True):
            verify_worker(worker.pk, self.admin, "APPROVED", "Verified identity")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [worker.user.email])
        self.assertIn("approved", mail.outbox[0].subject)

    def test_login_rate_limit(self):
        cache.set("login:127.0.0.1", 15, 300)
        response = self.client.post(reverse("login"), {"username": "bad", "password": "bad"})
        self.assertEqual(response.status_code, 429)
