from django.core.exceptions import PermissionDenied
from django.db import transaction
from jobs.services import WorkflowError
from notifications.services import notify

from .models import Review


@transaction.atomic
def create_review(model, service_id, customer, rating, text):
    service = model.objects.select_for_update().get(pk=service_id)
    if customer.role != "CUSTOMER" or service.customer_id != customer.pk:
        raise PermissionDenied
    if service.status != "COMPLETED" or not service.worker_id:
        raise WorkflowError("Complete this service before leaving a review.")
    if Review.objects.filter(**{service.kind: service}).exists():
        raise WorkflowError("You have already reviewed this service.")
    review = Review(
        customer=customer,
        worker=service.worker,
        **{service.kind: service},
        rating=rating,
        text=text,
    )
    review.full_clean()
    review.save()
    notify(
        service.worker.user,
        "REVIEW",
        "You received a new review",
        f"{rating}/5 for {service.title}",
        service.pk,
    )
    return review
