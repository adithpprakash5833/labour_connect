from accounts.decorators import admin_required
from accounts.models import User
from complaints.models import Complaint
from core.models import ServiceCategory
from core.presentation import SERVICE_COLUMNS, service_rows
from core.utils import monthly_series, paginate, status_series
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from jobs.models import Booking, Job
from payments.models import Payment
from workers.models import WorkerProfile

from .forms import AnnouncementForm, CategoryForm, VerificationForm
from .models import Announcement
from .services import publish_announcement, verify_worker


@admin_required
def dashboard(request):
    jobs = Job.objects.select_related("customer", "category", "worker__user")
    bookings = Booking.objects.select_related("customer", "category", "worker__user")
    paid = Payment.objects.filter(payment_status="PAID")
    stats = [
        ("Total users", User.objects.count(), "people"),
        ("Customers", User.objects.filter(role="CUSTOMER").count(), "person"),
        ("Workers", WorkerProfile.objects.count(), "tools"),
        (
            "Pending approvals",
            WorkerProfile.objects.filter(verification_status="PENDING").count(),
            "shield-exclamation",
        ),
        (
            "Approved workers",
            WorkerProfile.objects.filter(verification_status="APPROVED").count(),
            "shield-check",
        ),
        (
            "Active jobs",
            jobs.filter(status__in=["ACCEPTED", "IN_PROGRESS"]).count()
            + bookings.filter(status__in=["ACCEPTED", "IN_PROGRESS"]).count(),
            "lightning",
        ),
        (
            "Completed jobs",
            jobs.filter(status="COMPLETED").count() + bookings.filter(status="COMPLETED").count(),
            "check2-circle",
        ),
        (
            "Paid records",
            "₹{:,.2f}".format(paid.aggregate(total=Sum("amount"))["total"] or 0),
            "credit-card",
        ),
        (
            "Open complaints",
            Complaint.objects.filter(status__in=["PENDING", "IN_REVIEW"]).count(),
            "chat-square-text",
        ),
    ]
    roles = list(User.objects.values("role").annotate(value=Count("pk")).order_by("role"))
    return render(
        request,
        "dashboard/overview.html",
        {
            "title": "Platform overview",
            "stats": stats,
            "chart": monthly_series(User.objects.all(), date_field="date_joined"),
            "chart_title": "Monthly registrations",
            "chart_secondary": {
                "labels": [x["role"].title() for x in roles],
                "values": [x["value"] for x in roles],
            },
            "chart_secondary_title": "Users by role",
            "recent_rows": service_rows(bookings[:5]),
            "recent_job_rows": service_rows(jobs[:5]),
            "columns": SERVICE_COLUMNS,
            "recent_notifications": request.user.notifications.all()[:4],
        },
    )


@admin_required
def users(request, role=None):
    qs = User.objects.all().order_by("-date_joined")
    chosen = role or request.GET.get("role")
    if chosen:
        qs = qs.filter(role=chosen)
    if request.GET.get("q"):
        term = request.GET["q"]
        qs = qs.filter(
            Q(username__icontains=term)
            | Q(email__icontains=term)
            | Q(first_name__icontains=term)
            | Q(last_name__icontains=term)
        )
    page = paginate(request, qs)
    rows = [
        {
            "cells": [
                u.display_name,
                u.username,
                u.email,
                u.role.title(),
                u.date_joined.strftime("%d %b %Y"),
            ],
            "status": "ACTIVE" if u.is_active else "INACTIVE",
            "url": reverse("admin_user_detail", args=[u.pk]),
        }
        for u in page
    ]
    return render(
        request,
        "dashboard/records.html",
        {
            "title": "Customers" if chosen == "CUSTOMER" else "Users",
            "rows": rows,
            "columns": ["Name", "Username", "Email", "Role", "Joined"],
            "page_obj": page,
            "user_filter": role is None,
            "search_filter": True,
        },
    )


@admin_required
def user_detail(request, pk):
    user = get_object_or_404(User, pk=pk)
    return render(
        request, "adminpanel/user_detail.html", {"title": user.display_name, "account": user}
    )


@require_POST
@admin_required
def toggle_user(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user.pk == request.user.pk or user.is_superuser or user.role == "ADMINISTRATOR":
        raise PermissionDenied("Administrator accounts cannot be deactivated here.")
    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])
    messages.success(
        request,
        "Account activated."
        if user.is_active
        else "Account deactivated. Existing sessions will lose access.",
    )
    return redirect("admin_user_detail", pk=pk)


@admin_required
def workers(request, pending=False):
    qs = WorkerProfile.objects.select_related("user", "category")
    status = "PENDING" if pending else request.GET.get("status")
    if status:
        qs = qs.filter(verification_status=status)
    if request.GET.get("q"):
        term = request.GET["q"]
        qs = qs.filter(
            Q(user__first_name__icontains=term)
            | Q(user__last_name__icontains=term)
            | Q(designation__icontains=term)
        )
    page = paginate(request, qs)
    rows = [
        {
            "cells": [
                w.user.display_name,
                w.designation,
                w.category.name,
                w.working_area,
                f"₹{w.service_rate:,.2f}",
            ],
            "status": w.verification_status,
            "url": reverse("verify_worker", args=[w.pk]),
        }
        for w in page
    ]
    return render(
        request,
        "dashboard/records.html",
        {
            "title": "Pending verifications" if pending else "Workers",
            "rows": rows,
            "columns": ["Professional", "Designation", "Category", "Area", "Hourly rate"],
            "page_obj": page,
            "verification_filter": not pending,
            "search_filter": True,
        },
    )


@admin_required
def verification(request, pk):
    worker = get_object_or_404(
        WorkerProfile.objects.select_related("user", "category").prefetch_related(
            "documents", "verification_history__administrator"
        ),
        pk=pk,
    )
    form = VerificationForm(
        request.POST or None,
        initial={"status": worker.verification_status, "reason": worker.verification_reason},
    )
    if request.method == "POST" and form.is_valid():
        verify_worker(pk, request.user, form.cleaned_data["status"], form.cleaned_data["reason"])
        messages.success(request, "Verification decision saved and worker notified.")
        return redirect("verify_worker", pk=pk)
    return render(
        request,
        "adminpanel/verification.html",
        {"title": "Review professional", "worker": worker, "form": form},
    )


@admin_required
def categories(request):
    page = paginate(request, ServiceCategory.objects.all())
    rows = [
        {
            "cells": [c.name, c.slug, c.description],
            "status": "ACTIVE" if c.is_active else "INACTIVE",
            "url": reverse("category_edit", args=[c.pk]),
        }
        for c in page
    ]
    return render(
        request,
        "dashboard/records.html",
        {
            "title": "Service categories",
            "rows": rows,
            "columns": ["Name", "Slug", "Description"],
            "page_obj": page,
            "create_url": "category_create",
            "create_label": "Add category",
        },
    )


@admin_required
def category_edit(request, pk=None):
    category = get_object_or_404(ServiceCategory, pk=pk) if pk else None
    form = CategoryForm(request.POST or None, request.FILES or None, instance=category)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Category saved.")
        return redirect("admin_categories")
    return render(
        request,
        "dashboard/form.html",
        {
            "title": "Edit category" if pk else "Add category",
            "form": form,
            "submit_label": "Save category",
        },
    )


@admin_required
def services(request, kind):
    model = Job if kind == "job" else Booking
    qs = model.objects.select_related("customer", "worker__user", "category")
    if request.GET.get("status"):
        qs = qs.filter(status=request.GET["status"])
    page = paginate(request, qs)
    return render(
        request,
        "dashboard/records.html",
        {
            "title": "Jobs" if kind == "job" else "Bookings",
            "rows": service_rows(page),
            "columns": SERVICE_COLUMNS,
            "page_obj": page,
            "status_filter": True,
        },
    )


@admin_required
def announcements(request):
    form = AnnouncementForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        publish_announcement(form, request.user)
        messages.success(request, "Announcement published to the selected audience.")
        return redirect("announcements")
    page = paginate(request, Announcement.objects.select_related("created_by"))
    return render(
        request,
        "adminpanel/announcements.html",
        {"title": "Announcements", "form": form, "announcements": page, "page_obj": page},
    )


@admin_required
def analytics(request):
    paid = Payment.objects.filter(payment_status="PAID")
    category_rows = list(
        ServiceCategory.objects.annotate(
            job_count=Count("job_services", distinct=True),
            booking_count=Count("booking_services", distinct=True),
        ).order_by("name")
    )
    verification = list(
        WorkerProfile.objects.values("verification_status")
        .annotate(value=Count("pk"))
        .order_by("verification_status")
    )
    total = Job.objects.count() + Booking.objects.count()
    completed = (
        Job.objects.filter(status="COMPLETED").count()
        + Booking.objects.filter(status="COMPLETED").count()
    )
    charts = [
        {
            "title": "User growth",
            "type": "line",
            "data": monthly_series(User.objects.all(), date_field="date_joined"),
        },
        {
            "title": "Monthly open job creation",
            "type": "bar",
            "data": monthly_series(Job.objects.all()),
        },
        {"title": "Monthly bookings", "type": "bar", "data": monthly_series(Booking.objects.all())},
        {
            "title": "Paid records by creation month (₹)",
            "type": "line",
            "data": monthly_series(paid, "amount"),
        },
        {
            "title": "Worker verification",
            "type": "doughnut",
            "data": {
                "labels": [x["verification_status"].title() for x in verification],
                "values": [x["value"] for x in verification],
            },
        },
        {
            "title": "Services by category",
            "type": "bar",
            "data": {
                "labels": [c.name for c in category_rows],
                "values": [c.job_count + c.booking_count for c in category_rows],
            },
        },
        {"title": "Jobs by status", "type": "doughnut", "data": status_series(Job.objects.all())},
        {
            "title": "Complaint status",
            "type": "doughnut",
            "data": status_series(Complaint.objects.all()),
        },
    ]
    from django.db.models import Avg

    top_workers = (
        WorkerProfile.objects.filter(verification_status="APPROVED", user__is_active=True)
        .select_related("user", "category")
        .annotate(rating=Avg("reviews__rating"), review_count=Count("reviews", distinct=True))
        .order_by("-rating")[:4]
    )
    return render(
        request,
        "adminpanel/analytics.html",
        {
            "title": "Platform analytics",
            "charts": charts,
            "completion_rate": round(completed / total * 100, 1) if total else 0,
            "completed": completed,
            "total": total,
            "top_workers": top_workers,
        },
    )
