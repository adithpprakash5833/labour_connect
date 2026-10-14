import uuid

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from jobs.services import WorkflowError
from notifications.services import notify

from .models import Payment


class DemoPaymentProvider:
    """Academic simulator. Replace with a gateway adapter and verified webhooks for real money."""

    @staticmethod
    def settle():
        return "DEMO-" + uuid.uuid4().hex[:16].upper()


@transaction.atomic
def record_payment(model, service_id, customer, method, reference=""):
    service = model.objects.select_for_update().get(pk=service_id)
    if customer.role != "CUSTOMER" or service.customer_id != customer.pk:
        raise PermissionDenied
    if service.status != "COMPLETED" or not service.worker_id:
        raise WorkflowError("Payments can be recorded only for completed services.")
    field = service.kind
    if Payment.objects.filter(**{field: service}).exists():
        raise WorkflowError("A payment record already exists for this service.")
    if method not in Payment.Method.values:
        raise WorkflowError("Choose a valid payment method.")
    if method == "UPI" and not reference.strip():
        raise WorkflowError("A UPI transaction reference is required.")
    paid = method == "DEMO"
    payment = Payment.objects.create(
        customer=customer,
        worker=service.worker,
        **{field: service},
        amount=service.budget,
        payment_method=method,
        transaction_reference=DemoPaymentProvider.settle() if paid else reference,
        payment_status="PAID" if paid else "PENDING",
        payment_date=timezone.now() if paid else None,
    )
    notify(
        service.worker.user,
        "PAYMENT_COMPLETED" if paid else "PAYMENT_CREATED",
        "Payment recorded",
        f"₹{payment.amount} for {service.title}. {payment.get_payment_status_display()}.",
        service.pk,
    )
    notify(
        customer,
        "PAYMENT_CREATED",
        "Your payment record",
        f"{service.title}: ₹{payment.amount}.",
        service.pk,
    )
    return payment


@transaction.atomic
def change_payment(payment_id, actor, target):
    payment = Payment.objects.select_for_update().get(pk=payment_id)
    is_owner = (
        actor.role == "WORKER"
        and payment.worker.user_id == actor.pk
        and actor.worker_profile.verification_status == "APPROVED"
    )
    is_admin = actor.role == "ADMINISTRATOR"
    if not (is_owner or is_admin):
        raise PermissionDenied
    allowed = {"PENDING": ["PAID", "FAILED"], "PAID": ["REFUNDED"] if is_admin else []}
    if target not in allowed.get(payment.payment_status, []):
        raise WorkflowError("This payment status change is not permitted.")
    payment.payment_status = target
    if target == "PAID":
        payment.payment_date = timezone.now()
    payment.save(update_fields=["payment_status", "payment_date", "updated_at"])
    for recipient in (payment.customer, payment.worker.user):
        notify(
            recipient,
            "PAYMENT_STATUS",
            f"Payment {target.lower()}",
            f"{payment.service.title}: ₹{payment.amount}",
            payment.pk,
        )
    return payment
