from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from notifications.services import notify

from .models import Job


class WorkflowError(ValidationError):
    pass


def ensure_approved(worker):
    if (
        worker.user.role != "WORKER"
        or not worker.user.is_active
        or worker.verification_status != "APPROVED"
    ):
        raise PermissionDenied("An active, approved worker is required.")


def can_view_service(user, service):
    return (
        user.role == "ADMINISTRATOR"
        or service.customer_id == user.pk
        or (service.worker_id and service.worker.user_id == user.pk)
        or (
            isinstance(service, Job)
            and service.status == "OPEN"
            and user.role == "WORKER"
            and user.is_active
            and getattr(user, "worker_profile", None)
            and user.worker_profile.verification_status == "APPROVED"
        )
    )


def actions_for(user, service):
    if user.pk == service.customer_id and user.role == "CUSTOMER":
        return ["CANCELLED"] if service.status in ("OPEN", "REQUESTED", "ACCEPTED") else []
    profile = getattr(user, "worker_profile", None)
    if user.role != "WORKER" or not profile or profile.verification_status != "APPROVED":
        return []
    if isinstance(service, Job) and service.status == "OPEN" and not service.worker_id:
        return ["ACCEPTED"]
    if service.worker_id != profile.pk:
        return []
    return {
        "REQUESTED": ["ACCEPTED", "REJECTED"],
        "ACCEPTED": ["IN_PROGRESS"],
        "IN_PROGRESS": ["COMPLETED"],
    }.get(service.status, [])


@transaction.atomic
def accept_open_job(job_id, worker):
    """Lock the indexed primary key; only the first transaction can assign a worker."""
    ensure_approved(worker)
    job = Job.objects.select_for_update().get(pk=job_id)
    if job.worker_id:
        raise WorkflowError("This job has already been assigned.")
    if job.status != "OPEN" or not job.category.is_active or not job.customer.is_active:
        raise WorkflowError("This job is no longer available.")
    job.worker = worker
    job.status = "ACCEPTED"
    job.save(update_fields=["worker", "status", "updated_at"])
    notify(
        job.customer,
        "JOB_ACCEPTED",
        "Your job has been accepted",
        f"{worker.user.display_name} accepted “{job.title}”.",
        job.pk,
    )
    notify(worker.user, "JOB_ACCEPTED", "Job assigned to you", job.title, job.pk)
    return job


@transaction.atomic
def transition_service(model, service_id, actor, target):
    if model is Job and target == "ACCEPTED":
        if actor.role != "WORKER":
            raise PermissionDenied
        return accept_open_job(service_id, actor.worker_profile)
    service = model.objects.select_for_update().get(pk=service_id)
    if not can_view_service(actor, service):
        raise PermissionDenied
    if actor.role == "WORKER":
        ensure_approved(actor.worker_profile)
    if target not in actions_for(actor, service):
        raise WorkflowError(
            f"Cannot change {service.get_status_display()} to {target.replace('_', ' ').lower()}."
        )
    service.status = target
    if target == "COMPLETED":
        service.completed_at = timezone.now()
    service.save(update_fields=["status", "completed_at", "updated_at"])
    recipient = (
        service.worker.user
        if actor.pk == service.customer_id and service.worker_id
        else service.customer
    )
    notify(
        recipient,
        "SERVICE_STATUS",
        f"Service {service.get_status_display().lower()}",
        service.title,
        service.pk,
    )
    return service


@transaction.atomic
def create_booking(form, customer, worker):
    if customer.role != "CUSTOMER":
        raise PermissionDenied
    worker = (
        type(worker)
        .objects.select_for_update()
        .select_related("user", "category")
        .get(pk=worker.pk)
    )
    ensure_approved(worker)
    if not worker.category.is_active or worker.availability_status != "AVAILABLE":
        raise WorkflowError("This worker is currently unavailable for new bookings.")
    booking = form.save(commit=False)
    booking.customer = customer
    booking.worker = worker
    booking.category = worker.category
    booking.status = "REQUESTED"
    booking.save()
    notify(
        worker.user,
        "BOOKING_REQUEST",
        "New booking request",
        f"{customer.display_name}: {booking.title}",
        booking.pk,
    )
    return booking
