from datetime import date, datetime
from datetime import timezone as dt_timezone
from unittest.mock import patch

from accounts.models import User
from django.test import TestCase
from jobs.models import Booking

from core.utils import monthly_series

from .helpers import make_user, make_worker, service_data


class MetricsTests(TestCase):
    def test_user_growth_counts_database_users_without_named_timezone_tables(self):
        make_user("customer")
        series = monthly_series(User.objects.all(), date_field="date_joined")
        self.assertEqual(sum(series["values"]), 1)
        self.assertEqual(len(series["labels"]), 6)

    @patch("core.utils.timezone.localdate", return_value=date(2026, 10, 6))
    def test_month_boundaries_follow_indian_local_time(self, localdate):
        customer = make_user("customer")
        worker = make_worker()
        booking = Booking.objects.create(
            customer=customer, worker=worker, **service_data(worker.category)
        )
        Booking.objects.filter(pk=booking.pk).update(
            created_at=datetime(2026, 9, 30, 21, 0, tzinfo=dt_timezone.utc)
        )
        series = monthly_series(Booking.objects.all())
        self.assertEqual(series["values"][-1], 1)
        self.assertEqual(series["values"][-2], 0)
