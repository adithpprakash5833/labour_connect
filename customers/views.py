from accounts.decorators import customer_required
from core.presentation import SERVICE_COLUMNS, service_rows
from core.utils import monthly_series, paginate, status_series
from django.db.models import Sum
from django.shortcuts import render
from jobs.models import Booking, Job
from workers.search import search_workers


@customer_required
def dashboard(request):
    bookings = Booking.objects.filter(customer=request.user).select_related(
        "category", "customer", "worker__user"
    )
    jobs = Job.objects.filter(customer=request.user).select_related(
        "category", "customer", "worker__user"
    )
    paid = request.user.payments.filter(payment_status="PAID")
    stats = [
        ("Total requests", bookings.count() + jobs.count(), "calendar2-check"),
        (
            "Active jobs",
            bookings.filter(status__in=["ACCEPTED", "IN_PROGRESS"]).count()
            + jobs.filter(status__in=["ACCEPTED", "IN_PROGRESS"]).count(),
            "lightning",
        ),
        (
            "Completed jobs",
            bookings.filter(status="COMPLETED").count() + jobs.filter(status="COMPLETED").count(),
            "check2-circle",
        ),
        (
            "Pending requests",
            bookings.filter(status="REQUESTED").count() + jobs.filter(status="OPEN").count(),
            "hourglass-split",
        ),
        (
            "Total payments",
            "₹{:,.2f}".format(paid.aggregate(total=Sum("amount"))["total"] or 0),
            "credit-card",
        ),
        ("Unread notifications", request.user.notifications.filter(is_read=False).count(), "bell"),
    ]
    params = (
        {
            "latitude": str(request.user.latitude),
            "longitude": str(request.user.longitude),
            "sort": "nearest",
        }
        if request.user.latitude is not None and request.user.longitude is not None
        else {}
    )
    return render(
        request,
        "dashboard/overview.html",
        {
            "title": "Your service hub",
            "stats": stats,
            "chart": monthly_series(bookings),
            "chart_title": "Monthly booking activity",
            "chart_secondary": status_series(jobs),
            "chart_secondary_title": "Jobs by status",
            "recent_rows": service_rows(bookings[:5]),
            "recent_job_rows": service_rows(jobs[:5]),
            "columns": SERVICE_COLUMNS,
            "recent_notifications": request.user.notifications.all()[:4],
            "recommended": search_workers(params)[:4],
        },
    )


@customer_required
def my_jobs(request):
    qs = Job.objects.filter(customer=request.user).select_related(
        "customer", "worker__user", "category"
    )
    if request.GET.get("status"):
        qs = qs.filter(status=request.GET["status"])
    page = paginate(request, qs)
    return render(
        request,
        "dashboard/records.html",
        {
            "title": "My jobs",
            "rows": service_rows(page),
            "columns": SERVICE_COLUMNS,
            "page_obj": page,
            "status_filter": True,
            "create_url": "post_job",
            "create_label": "Post a job",
        },
    )


@customer_required
def bookings(request):
    qs = Booking.objects.filter(customer=request.user).select_related(
        "customer", "worker__user", "category"
    )
    if request.GET.get("status"):
        qs = qs.filter(status=request.GET["status"])
    page = paginate(request, qs)
    return render(
        request,
        "dashboard/records.html",
        {
            "title": "My bookings",
            "rows": service_rows(page),
            "columns": SERVICE_COLUMNS,
            "page_obj": page,
            "status_filter": True,
            "create_url": "find_workers",
            "create_label": "Find a worker",
        },
    )
