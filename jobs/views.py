from accounts.decorators import customer_required, platform_member_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from workers.models import WorkerProfile

from .forms import BookingForm, JobForm, TransitionForm
from .models import Booking, Job
from .services import (
    WorkflowError,
    actions_for,
    can_view_service,
    create_booking,
    transition_service,
)


def service_model(kind):
    from django.http import Http404

    if kind not in ("booking", "job"):
        raise Http404
    return Booking if kind == "booking" else Job


@customer_required
def book_worker(request, pk):
    worker = get_object_or_404(
        WorkerProfile.objects.select_related("user", "category"),
        pk=pk,
        verification_status="APPROVED",
        user__is_active=True,
        category__is_active=True,
    )
    form = BookingForm(
        request.POST or None,
        initial={
            "address": request.user.address,
            "latitude": request.user.latitude,
            "longitude": request.user.longitude,
        },
    )
    if request.method == "POST" and form.is_valid():
        try:
            booking = create_booking(form, request.user, worker)
        except WorkflowError as exc:
            form.add_error(None, exc)
        else:
            messages.success(
                request, "Request sent. We will notify you when the professional responds."
            )
            return redirect("service_detail", kind="booking", pk=booking.pk)
    return render(
        request,
        "dashboard/form.html",
        {
            "title": f"Book {worker.user.display_name}",
            "subtitle": f"{worker.designation} · ₹{worker.service_rate}/hour. Your budget is the total agreed service amount.",
            "form": form,
            "submit_label": "Send booking request",
        },
    )


@customer_required
def post_job(request):
    form = JobForm(
        request.POST or None,
        initial={
            "address": request.user.address,
            "latitude": request.user.latitude,
            "longitude": request.user.longitude,
        },
    )
    if request.method == "POST" and form.is_valid():
        job = form.save(commit=False)
        job.customer = request.user
        job.status = "OPEN"
        job.save()
        messages.success(request, "Job published. Verified workers can now accept it.")
        return redirect("service_detail", kind="job", pk=job.pk)
    return render(
        request,
        "dashboard/form.html",
        {
            "title": "Post a local job",
            "subtitle": "Describe what you need. A verified professional will accept your request.",
            "form": form,
            "submit_label": "Publish job",
        },
    )


@platform_member_required
def service_detail(request, kind, pk):
    service = get_object_or_404(
        service_model(kind).objects.select_related("customer", "worker__user", "category"), pk=pk
    )
    if not can_view_service(request.user, service):
        raise PermissionDenied
    return render(
        request,
        "jobs/detail.html",
        {
            "title": service.title,
            "service": service,
            "actions": actions_for(request.user, service),
            "is_customer_owner": service.customer_id == request.user.pk,
            "payment": getattr(service, "payment", None),
            "review": getattr(service, "review", None),
        },
    )


@require_POST
@platform_member_required
def transition(request, kind, pk):
    model = service_model(kind)
    get_object_or_404(model, pk=pk)
    form = TransitionForm(request.POST)
    if form.is_valid():
        try:
            transition_service(model, pk, request.user, form.cleaned_data["target"])
        except WorkflowError as exc:
            messages.error(request, " ".join(exc.messages))
        else:
            messages.success(request, "Service status updated.")
    else:
        messages.error(request, "Choose a valid service action.")
    # A racing worker loses visibility after another worker takes an open job.
    updated = model.objects.get(pk=pk)
    if not can_view_service(request.user, updated):
        return redirect("available_jobs")
    return redirect("service_detail", kind=kind, pk=pk)
