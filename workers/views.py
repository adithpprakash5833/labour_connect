from accounts.decorators import approved_worker_required, platform_member_required
from core.models import ServiceCategory
from core.presentation import SERVICE_COLUMNS, service_rows
from core.utils import monthly_series, paginate, status_series
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from jobs.models import Job

from .forms import AvailabilityForm, DocumentForm
from .models import WorkerDocument, WorkerProfile
from .search import search_workers


def find_workers(request):
    workers = search_workers(request.GET)
    page = paginate(request, workers, 9)
    return render(
        request,
        "public/find_workers.html",
        {
            "page_obj": page,
            "workers": page,
            "categories": ServiceCategory.objects.filter(is_active=True),
            "title": "Find your next professional",
        },
    )


def worker_detail(request, pk):
    worker = get_object_or_404(
        WorkerProfile.objects.select_related("user", "category"),
        pk=pk,
        user__is_active=True,
        verification_status="APPROVED",
        category__is_active=True,
    )
    review_page = paginate(request, worker.reviews.select_related("customer"), 6)
    return render(
        request,
        "public/worker_detail.html",
        {
            "worker": worker,
            "reviews": review_page,
            "page_obj": review_page,
            "title": worker.user.display_name,
        },
    )


@approved_worker_required
def dashboard(request):
    worker = request.user.worker_profile
    bookings = worker.bookings.select_related("customer", "category", "worker__user")
    jobs = worker.jobs.select_related("customer", "category", "worker__user")
    paid = worker.payments.filter(payment_status="PAID")
    stats = [
        ("Pending requests", bookings.filter(status="REQUESTED").count(), "inbox"),
        (
            "Accepted jobs",
            bookings.filter(status="ACCEPTED").count() + jobs.filter(status="ACCEPTED").count(),
            "calendar2-check",
        ),
        (
            "Active jobs",
            bookings.filter(status="IN_PROGRESS").count()
            + jobs.filter(status="IN_PROGRESS").count(),
            "lightning",
        ),
        ("Completed jobs", worker.total_completed_jobs, "check2-circle"),
        (
            "Total earnings",
            "₹{:,.2f}".format(paid.aggregate(total=Sum("amount"))["total"] or 0),
            "wallet2",
        ),
        ("Average rating", f"{worker.average_rating:.1f} / 5", "star"),
    ]
    job_months = monthly_series(jobs.filter(status="COMPLETED"), date_field="completed_at")
    booking_months = monthly_series(bookings.filter(status="COMPLETED"), date_field="completed_at")
    job_months["values"] = [a + b for a, b in zip(job_months["values"], booking_months["values"])]
    return render(
        request,
        "dashboard/overview.html",
        {
            "title": "Worker workspace",
            "stats": stats,
            "chart": monthly_series(paid, "amount", date_field="payment_date"),
            "chart_title": "Monthly earnings (₹)",
            "chart_secondary": status_series(bookings),
            "chart_secondary_title": "Bookings by status",
            "chart_extra": job_months,
            "chart_extra_title": "Services completed per month",
            "recent_rows": service_rows(bookings[:5]),
            "columns": SERVICE_COLUMNS,
            "recent_notifications": request.user.notifications.all()[:4],
            "recent_reviews": worker.reviews.select_related("customer")[:3],
            "availability_form": AvailabilityForm(instance=worker),
        },
    )


@approved_worker_required
def available_jobs(request):
    qs = Job.objects.filter(
        status="OPEN", worker__isnull=True, customer__is_active=True, category__is_active=True
    ).select_related("customer", "category", "worker__user")
    from .search import number

    if request.GET.get("category"):
        qs = qs.filter(category__slug=request.GET["category"])
    if request.GET.get("location"):
        qs = qs.filter(address__icontains=request.GET["location"])
    for key, lookup in [("min_budget", "budget__gte"), ("max_budget", "budget__lte")]:
        value = number(request.GET.get(key), 0)
        if value is not None:
            qs = qs.filter(**{lookup: value})
    if request.GET.get("urgent") == "1":
        qs = qs.filter(urgent=True)
    if request.GET.get("date"):
        from django.utils.dateparse import parse_date

        try:
            date = parse_date(request.GET["date"])
        except ValueError:
            date = None
        if date:
            qs = qs.filter(job_date=date)
    page = paginate(request, qs)
    return render(
        request,
        "jobs/available.html",
        {
            "title": "Available jobs",
            "jobs": page,
            "page_obj": page,
            "categories": ServiceCategory.objects.filter(is_active=True),
        },
    )


@approved_worker_required
def my_jobs(request):
    qs = request.user.worker_profile.jobs.select_related("customer", "category", "worker__user")
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
        },
    )


@approved_worker_required
def bookings(request):
    qs = request.user.worker_profile.bookings.select_related("customer", "category", "worker__user")
    if request.GET.get("status"):
        qs = qs.filter(status=request.GET["status"])
    page = paginate(request, qs)
    return render(
        request,
        "dashboard/records.html",
        {
            "title": "Booking requests",
            "rows": service_rows(page),
            "columns": SERVICE_COLUMNS,
            "page_obj": page,
            "status_filter": True,
        },
    )


@approved_worker_required
def availability(request):
    form = AvailabilityForm(request.POST or None, instance=request.user.worker_profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Availability updated. Customers will see your new status.")
        return redirect("worker_dashboard")
    return render(
        request,
        "dashboard/form.html",
        {
            "title": "Your availability",
            "subtitle": "Control when customers can send new booking requests.",
            "form": form,
            "submit_label": "Save availability",
        },
    )


@approved_worker_required
def documents(request):
    form = DocumentForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        document = form.save(commit=False)
        document.worker = request.user.worker_profile
        document.save()
        from accounts.models import User
        from notifications.services import notify

        for admin in User.objects.filter(role="ADMINISTRATOR", is_active=True):
            notify(
                admin,
                "DOCUMENT",
                "New worker document",
                request.user.display_name,
                document.worker_id,
            )
        messages.success(request, "Document uploaded privately for administrator review.")
        return redirect("documents")
    return render(
        request,
        "worker/documents.html",
        {
            "title": "Private documents",
            "form": form,
            "documents": request.user.worker_profile.documents.all(),
        },
    )


@platform_member_required
def download_document(request, pk):
    document = get_object_or_404(WorkerDocument.objects.select_related("worker"), pk=pk)
    if request.user.role != "ADMINISTRATOR" and document.worker.user_id != request.user.pk:
        raise PermissionDenied
    try:
        response = FileResponse(
            document.document_file.open("rb"),
            as_attachment=True,
            filename=f"{document.get_document_type_display()}{__import__('pathlib').Path(document.document_file.name).suffix}",
        )
    except FileNotFoundError:
        raise Http404("Document file not found.")
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
