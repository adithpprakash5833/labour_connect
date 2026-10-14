from accounts.models import User
from adminpanel.models import Announcement
from django.conf import settings
from django.db.models import Q
from django.urls import reverse
from jobs.models import ServiceStatus
from payments.models import Payment
from workers.models import WorkerProfile

MENUS = {
    "CUSTOMER": [
        ("Dashboard", "customer_dashboard", "grid"),
        ("Find workers", "find_workers", "search"),
        ("Post a job", "post_job", "plus-circle"),
        ("My jobs", "customer_jobs", "briefcase"),
        ("My bookings", "customer_bookings", "calendar2-check"),
        ("Payments", "payments", "credit-card"),
        ("Reviews", "reviews", "star"),
        ("Notifications", "notifications", "bell"),
        ("Complaints", "complaints", "chat-square-text"),
        ("My profile", "profile", "person"),
        ("Settings", "settings", "gear"),
    ],
    "WORKER": [
        ("Dashboard", "worker_dashboard", "grid"),
        ("Booking requests", "worker_bookings", "calendar2-check"),
        ("Available jobs", "available_jobs", "search"),
        ("My jobs", "worker_jobs", "briefcase"),
        ("Earnings", "payments", "wallet2"),
        ("Ratings & reviews", "reviews", "star"),
        ("Notifications", "notifications", "bell"),
        ("My profile", "profile", "person"),
        ("Availability", "availability", "toggle-on"),
        ("Documents", "documents", "file-earmark-lock"),
        ("Complaints", "complaints", "chat-square-text"),
        ("Settings", "settings", "gear"),
    ],
    "ADMINISTRATOR": [
        ("Dashboard", "admin_dashboard", "grid"),
        ("Users", "admin_users", "people"),
        ("Customers", "admin_customers", "person"),
        ("Workers", "admin_workers", "tools"),
        ("Pending verifications", "admin_verifications", "shield-check"),
        ("Categories", "admin_categories", "collection"),
        ("Jobs", "admin_jobs", "briefcase"),
        ("Bookings", "admin_bookings", "calendar2-check"),
        ("Payments", "payments", "credit-card"),
        ("Reviews", "reviews", "star"),
        ("Complaints", "complaints", "chat-square-text"),
        ("Notifications", "notifications", "bell"),
        ("Announcements", "announcements", "megaphone"),
        ("Analytics", "analytics", "bar-chart"),
        ("Settings", "settings", "gear"),
    ],
}


def platform(request):
    data = {
        "maps_key": settings.GOOGLE_MAPS_API_KEY,
        "maps_id": settings.GOOGLE_MAPS_MAP_ID,
        "service_status_choices": ServiceStatus.choices,
        "payment_status_choices": Payment.Status.choices,
        "verification_status_choices": WorkerProfile.Verification.choices,
        "role_choices": User.Role.choices,
    }
    if request.user.is_authenticated:
        data["dashboard_announcements"] = Announcement.objects.filter(
            Q(audience="ALL") | Q(audience=request.user.role)
        )[:2]
        data["unread_count"] = request.user.notifications.filter(is_read=False).count()
        data["nav_notifications"] = request.user.notifications.all()[:5]
        data["sidebar_items"] = [
            {
                "label": a,
                "url": reverse(b),
                "icon": c,
                "active": request.resolver_match and request.resolver_match.url_name == b,
            }
            for a, b, c in MENUS.get(request.user.role, [])
        ]
    return data
