from accounts.models import User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from jobs.services import WorkflowError
from notifications.models import Notification
from notifications.services import notify
from workers.models import VerificationEvent, WorkerProfile


@transaction.atomic
def verify_worker(worker_id, admin, status, reason=""):
    if admin.role != "ADMINISTRATOR":
        raise PermissionDenied
    if status not in WorkerProfile.Verification.values or (
        status == "REJECTED" and not reason.strip()
    ):
        raise WorkflowError("A valid decision and rejection reason are required.")
    worker = WorkerProfile.objects.select_for_update().get(pk=worker_id)
    worker.verification_status = status
    worker.verification_reason = reason
    worker.save(update_fields=["verification_status", "verification_reason", "updated_at"])
    worker.documents.update(verification_status=status, admin_note=reason)
    VerificationEvent.objects.create(
        worker=worker, administrator=admin, status=status, reason=reason
    )
    notify(
        worker.user,
        "VERIFICATION",
        f"Worker verification {status.lower()}",
        reason or "You may now sign in and accept work."
        if status == "APPROVED"
        else reason or "Your verification is awaiting review.",
        worker.pk,
    )
    return worker


@transaction.atomic
def publish_announcement(form, admin):
    if admin.role != "ADMINISTRATOR":
        raise PermissionDenied
    item = form.save(commit=False)
    item.created_by = admin
    item.save()
    users = User.objects.filter(is_active=True)
    if item.audience != "ALL":
        users = users.filter(role=item.audience)
    Notification.objects.bulk_create(
        [
            Notification(
                recipient=user,
                notification_type="ANNOUNCEMENT",
                title=item.title,
                message=item.message,
                related_object_id=item.pk,
            )
            for user in users.iterator()
        ],
        batch_size=500,
    )
    return item
