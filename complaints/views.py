from accounts.decorators import platform_member_required
from accounts.models import User
from core.utils import paginate
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from notifications.services import notify

from .forms import ComplaintForm, ComplaintResponseForm
from .models import Complaint


@platform_member_required
def complaints(request):
    qs = Complaint.objects.select_related(
        "created_by", "against_user", "related_job", "related_booking"
    )
    if request.user.role != "ADMINISTRATOR":
        qs = qs.filter(created_by=request.user)
    if request.GET.get("status"):
        qs = qs.filter(status=request.GET["status"])
    page = paginate(request, qs)
    return render(
        request,
        "complaints/list.html",
        {"title": "Support & complaints", "complaints": page, "page_obj": page},
    )


@platform_member_required
def create(request):
    form = ComplaintForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            item = form.save(commit=False)
            item.created_by = request.user
            service = item.related_job or item.related_booking
            if service:
                item.against_user = (
                    service.worker.user
                    if service.customer_id == request.user.pk and service.worker_id
                    else service.customer
                    if service.customer_id != request.user.pk
                    else None
                )
            item.save()
            for admin in User.objects.filter(role="ADMINISTRATOR", is_active=True):
                notify(admin, "COMPLAINT", "New complaint", item.subject, item.pk)
            notify(request.user, "COMPLAINT", "Complaint received", item.subject, item.pk)
        messages.success(request, "Complaint submitted to our administrator.")
        return redirect("complaint_detail", pk=item.pk)
    return render(
        request,
        "dashboard/form.html",
        {
            "title": "Raise a complaint",
            "subtitle": "Choose a service from your own history, or leave it empty for a general support request.",
            "form": form,
            "submit_label": "Submit complaint",
        },
    )


@platform_member_required
def detail(request, pk):
    qs = Complaint.objects.select_related(
        "created_by", "against_user", "related_job", "related_booking"
    )
    if request.user.role != "ADMINISTRATOR":
        qs = qs.filter(created_by=request.user)
    item = get_object_or_404(qs, pk=pk)
    form = (
        ComplaintResponseForm(request.POST or None, instance=item)
        if request.user.role == "ADMINISTRATOR"
        else None
    )
    if request.method == "POST":
        from django.core.exceptions import PermissionDenied

        if not form:
            raise PermissionDenied
        if form.is_valid():
            with transaction.atomic():
                form.save()
                notify(
                    item.created_by,
                    "COMPLAINT_STATUS",
                    f"Complaint {item.get_status_display().lower()}",
                    item.admin_response or item.subject,
                    item.pk,
                )
            messages.success(request, "Response saved and complainant notified.")
            return redirect("complaint_detail", pk=pk)
    return render(
        request, "complaints/detail.html", {"title": item.subject, "complaint": item, "form": form}
    )
