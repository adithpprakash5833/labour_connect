from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

from accounts.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, close_old_connections, connections, transaction
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse
from jobs.models import Booking, Job
from jobs.services import WorkflowError, accept_open_job, transition_service
from notifications.models import Notification
from payments.models import Payment
from payments.services import change_payment, record_payment
from reviews.models import Review
from reviews.services import create_review

from .helpers import PASSWORD, make_user, make_worker, service_data


class WorkflowTests(TestCase):
    def setUp(self):
        self.customer = make_user("customer")
        self.other = make_user("other")
        self.worker = make_worker()
        self.worker2 = make_worker("worker2", category=self.worker.category)
        self.booking = Booking.objects.create(
            customer=self.customer, worker=self.worker, **service_data(self.worker.category)
        )
        self.job = Job.objects.create(
            customer=self.customer, required_skill="Wiring", **service_data(self.worker.category)
        )

    def completed(self, model=Booking):
        service = self.booking if model is Booking else self.job
        if model is Job:
            accept_open_job(service.pk, self.worker)
        else:
            transition_service(model, service.pk, self.worker.user, "ACCEPTED")
        transition_service(model, service.pk, self.worker.user, "IN_PROGRESS")
        transition_service(model, service.pk, self.worker.user, "COMPLETED")
        service.refresh_from_db()
        return service

    def test_direct_booking_creates_requested_and_notification(self):
        self.client.force_login(self.customer)
        data = service_data(self.worker.category)
        data.pop("category")
        data["job_date"] = data["job_date"].isoformat()
        data["preferred_time"] = "10:00"
        response = self.client.post(reverse("book_worker", args=[self.worker.pk]), data)
        self.assertEqual(response.status_code, 302)
        booking = Booking.objects.latest("pk")
        self.assertEqual(booking.status, "REQUESTED")
        self.assertEqual(booking.customer, self.customer)
        self.assertTrue(
            self.worker.user.notifications.filter(
                notification_type="BOOKING_REQUEST", related_object_id=booking.pk
            ).exists()
        )

    def test_worker_cannot_create_booking(self):
        self.client.force_login(self.worker.user)
        self.assertEqual(
            self.client.post(reverse("book_worker", args=[self.worker2.pk]), {}).status_code, 403
        )

    def test_unavailable_and_unapproved_booking_rejected(self):
        self.client.force_login(self.customer)
        self.worker.availability_status = "UNAVAILABLE"
        self.worker.save()
        data = service_data(self.worker.category)
        data.pop("category")
        data["job_date"] = data["job_date"].isoformat()
        data["preferred_time"] = "10:00"
        response = self.client.post(reverse("book_worker", args=[self.worker.pk]), data)
        self.assertContains(response, "currently unavailable")
        self.assertEqual(Booking.objects.count(), 1)
        self.worker.verification_status = "PENDING"
        self.worker.save()
        self.assertEqual(
            self.client.get(reverse("book_worker", args=[self.worker.pk])).status_code, 404
        )

    def test_booking_accept_and_reject_notify_customer(self):
        self.client.force_login(self.worker.user)
        response = self.client.post(
            reverse("service_transition", args=["booking", self.booking.pk]), {"target": "ACCEPTED"}
        )
        self.assertEqual(response.status_code, 302)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "ACCEPTED")
        self.assertTrue(
            self.customer.notifications.filter(notification_type="SERVICE_STATUS").exists()
        )
        second = Booking.objects.create(
            customer=self.customer, worker=self.worker, **service_data(self.worker.category)
        )
        self.client.post(
            reverse("service_transition", args=["booking", second.pk]), {"target": "REJECTED"}
        )
        second.refresh_from_db()
        self.assertEqual(second.status, "REJECTED")

    def test_valid_and_invalid_transitions(self):
        with self.assertRaises(WorkflowError):
            transition_service(Booking, self.booking.pk, self.worker.user, "COMPLETED")
        self.completed()
        self.assertEqual(self.booking.status, "COMPLETED")
        self.assertIsNotNone(self.booking.completed_at)
        for state in ("IN_PROGRESS", "ACCEPTED", "CANCELLED"):
            with self.assertRaises(WorkflowError):
                transition_service(Booking, self.booking.pk, self.worker.user, state)

    def test_rejected_service_is_terminal(self):
        transition_service(Booking, self.booking.pk, self.worker.user, "REJECTED")
        with self.assertRaises(WorkflowError):
            transition_service(Booking, self.booking.pk, self.worker.user, "IN_PROGRESS")

    def test_cancellation_rules(self):
        transition_service(Booking, self.booking.pk, self.customer, "CANCELLED")
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "CANCELLED")
        transition_service(Job, self.job.pk, self.customer, "CANCELLED")
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "CANCELLED")
        second = Booking.objects.create(
            customer=self.customer, worker=self.worker, **service_data(self.worker.category)
        )
        transition_service(Booking, second.pk, self.worker.user, "ACCEPTED")
        transition_service(Booking, second.pk, self.worker.user, "IN_PROGRESS")
        with self.assertRaises(WorkflowError):
            transition_service(Booking, second.pk, self.customer, "CANCELLED")

    def test_open_job_can_only_be_accepted_once(self):
        accept_open_job(self.job.pk, self.worker)
        with self.assertRaises(WorkflowError):
            accept_open_job(self.job.pk, self.worker2)
        self.job.refresh_from_db()
        self.assertEqual(self.job.worker, self.worker)
        self.assertTrue(
            self.customer.notifications.filter(notification_type="JOB_ACCEPTED").exists()
        )

    def test_disabled_category_job_cannot_be_accepted_through_direct_url(self):
        self.job.category.is_active = False
        self.job.category.save(update_fields=["is_active"])
        with self.assertRaises(WorkflowError):
            accept_open_job(self.job.pk, self.worker)
        self.job.refresh_from_db()
        self.assertIsNone(self.job.worker_id)

    def test_pending_worker_cannot_accept_open_job(self):
        self.worker.verification_status = "PENDING"
        self.worker.save()
        with self.assertRaises(PermissionDenied):
            accept_open_job(self.job.pk, self.worker)

    def test_unassigned_worker_and_unrelated_customer_cannot_update_or_view(self):
        for user in (self.other, self.worker2.user):
            self.client.force_login(user)
            self.assertEqual(
                self.client.get(
                    reverse("service_detail", args=["booking", self.booking.pk])
                ).status_code,
                403,
            )
            self.assertEqual(
                self.client.post(
                    reverse("service_transition", args=["booking", self.booking.pk]),
                    {"target": "ACCEPTED"},
                ).status_code,
                403,
            )

    def test_job_posting_and_filter_page(self):
        self.client.force_login(self.customer)
        data = service_data(self.worker.category)
        data["category"] = self.worker.category.pk
        data["job_date"] = data["job_date"].isoformat()
        data["preferred_time"] = "10:00"
        data["required_skill"] = "Wiring"
        self.assertEqual(self.client.post(reverse("post_job"), data).status_code, 302)
        self.assertEqual(Job.objects.latest("pk").status, "OPEN")
        self.client.force_login(self.worker.user)
        self.assertContains(
            self.client.get(
                reverse("available_jobs") + "?category=electrician&location=Kochi&min_budget=1000"
            ),
            "Electrical repair",
        )

    def test_past_date_and_invalid_budget_rejected(self):
        self.client.force_login(self.customer)
        data = service_data(self.worker.category)
        data["category"] = self.worker.category.pk
        data["job_date"] = "2000-01-01"
        data["preferred_time"] = "10:00"
        data["required_skill"] = "Wiring"
        data["budget"] = "-10"
        response = self.client.post(reverse("post_job"), data)
        self.assertContains(response, "future date")
        self.assertEqual(Job.objects.count(), 1)

    def test_demo_payment_and_database_earnings(self):
        self.completed()
        payment = record_payment(Booking, self.booking.pk, self.customer, "DEMO")
        self.assertEqual(payment.payment_status, "PAID")
        self.assertEqual(payment.amount, Decimal("1500"))
        self.assertTrue(payment.transaction_reference.startswith("DEMO-"))
        self.client.force_login(self.worker.user)
        self.assertContains(self.client.get(reverse("worker_dashboard")), "1,500.00")
        self.assertTrue(
            self.worker.user.notifications.filter(notification_type="PAYMENT_COMPLETED").exists()
        )

    def test_cash_and_upi_confirmation_and_refund(self):
        self.completed()
        payment = record_payment(
            Booking, self.booking.pk, self.customer, "UPI", "actual-upi-reference"
        )
        self.assertEqual(payment.payment_status, "PENDING")
        with self.assertRaises(PermissionDenied):
            change_payment(payment.pk, self.customer, "PAID")
        with self.assertRaises(PermissionDenied):
            change_payment(payment.pk, self.worker2.user, "PAID")
        change_payment(payment.pk, self.worker.user, "PAID")
        payment.refresh_from_db()
        self.assertIsNotNone(payment.payment_date)
        with self.assertRaises(WorkflowError):
            change_payment(payment.pk, self.worker.user, "REFUNDED")
        admin = User.objects.create_superuser("admin", "admin@example.com", PASSWORD)
        change_payment(payment.pk, admin, "REFUNDED")
        payment.refresh_from_db()
        self.assertEqual(payment.payment_status, "REFUNDED")

    def test_ineligible_duplicate_and_unrelated_payments_rejected(self):
        with self.assertRaises(WorkflowError):
            record_payment(Booking, self.booking.pk, self.customer, "DEMO")
        self.completed()
        with self.assertRaises(PermissionDenied):
            record_payment(Booking, self.booking.pk, self.other, "DEMO")
        with self.assertRaises(WorkflowError):
            record_payment(Booking, self.booking.pk, self.customer, "UPI", "")
        record_payment(Booking, self.booking.pk, self.customer, "CASH")
        with self.assertRaises(WorkflowError):
            record_payment(Booking, self.booking.pk, self.customer, "DEMO")

    def test_completed_review_updates_database_rating(self):
        self.completed()
        review = create_review(Booking, self.booking.pk, self.customer, 5, "Excellent work.")
        self.assertEqual(review.worker, self.worker)
        self.assertEqual(self.worker.average_rating, 5)
        self.assertEqual(self.worker.total_reviews, 1)

    def test_review_ineligible_unrelated_duplicate_and_range(self):
        with self.assertRaises(WorkflowError):
            create_review(Booking, self.booking.pk, self.customer, 4, "Good")
        self.completed()
        with self.assertRaises(PermissionDenied):
            create_review(Booking, self.booking.pk, self.other, 4, "Good")
        with self.assertRaises(ValidationError):
            create_review(Booking, self.booking.pk, self.customer, 6, "Good")
        create_review(Booking, self.booking.pk, self.customer, 4, "Good")
        with self.assertRaises(WorkflowError):
            create_review(Booking, self.booking.pk, self.customer, 5, "Again")

    def test_complete_open_job_payment_and_review(self):
        self.completed(Job)
        record_payment(Job, self.job.pk, self.customer, "DEMO")
        create_review(Job, self.job.pk, self.customer, 5, "Great help.")
        self.assertEqual(self.worker.total_completed_jobs, 1)

    def test_payment_and_review_http_forms(self):
        self.completed()
        self.client.force_login(self.customer)
        self.assertEqual(
            self.client.post(
                reverse("payment_create", args=["booking", self.booking.pk]),
                {"payment_method": "DEMO", "transaction_reference": ""},
            ).status_code,
            302,
        )
        self.assertEqual(
            self.client.post(
                reverse("review_create", args=["booking", self.booking.pk]),
                {"rating": "5", "text": "Excellent service"},
            ).status_code,
            302,
        )
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(reverse("payment_detail", args=[self.booking.payment.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse("review_create", args=["booking", self.booking.pk])
            ).status_code,
            404,
        )

    def test_notification_mark_read_and_ownership(self):
        notice = Notification.objects.create(
            recipient=self.customer, notification_type="TEST", title="Hello", message="Test"
        )
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.post(reverse("notification_read", args=[notice.pk])).status_code, 404
        )
        self.client.force_login(self.customer)
        response = self.client.post(
            reverse("notification_read", args=[notice.pk]), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.json()["unread"], 0)
        notice.refresh_from_db()
        self.assertTrue(notice.is_read)
        self.assertEqual(self.client.get(reverse("notifications_read_all")).status_code, 405)

    def test_database_payment_xor_and_review_rating_constraints(self):
        self.completed()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Payment.objects.create(
                customer=self.customer, worker=self.worker, amount=100, payment_method="CASH"
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Review.objects.create(
                customer=self.customer,
                worker=self.worker,
                booking=self.booking,
                rating=7,
                text="Invalid",
            )


class ConcurrentAcceptanceTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_real_concurrent_acceptance_has_one_winner(self):
        customer = make_user("customer")
        first = make_worker("first")
        second = make_worker("second", category=first.category)
        job = Job.objects.create(
            customer=customer, required_skill="Wiring", **service_data(first.category)
        )
        barrier = Barrier(2)

        def attempt(worker_id):
            close_old_connections()
            try:
                from workers.models import WorkerProfile

                worker = WorkerProfile.objects.select_related("user").get(pk=worker_id)
                barrier.wait(timeout=10)
                try:
                    accept_open_job(job.pk, worker)
                    return "accepted"
                except WorkflowError:
                    return "already assigned"
            finally:
                connections["default"].close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(attempt, [first.pk, second.pk]))
        self.assertCountEqual(results, ["accepted", "already assigned"])
        job.refresh_from_db()
        self.assertIn(job.worker_id, [first.pk, second.pk])
        self.assertEqual(job.status, "ACCEPTED")
        self.assertEqual(customer.notifications.filter(notification_type="JOB_ACCEPTED").count(), 1)
