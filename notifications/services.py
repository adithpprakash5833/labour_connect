import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from .models import Notification

logger = logging.getLogger(__name__)


def notify(recipient, kind, title, message, related_id=None):
    notice = Notification.objects.create(
        recipient=recipient,
        notification_type=kind,
        title=title,
        message=message,
        related_object_id=related_id,
    )
    if settings.SEND_NOTIFICATION_EMAIL:

        def deliver():
            try:
                send_mail(title, message, settings.DEFAULT_FROM_EMAIL, [recipient.email])
            except Exception:
                logger.exception(
                    "Notification email delivery failed for notification %s", notice.pk
                )

        transaction.on_commit(deliver)
    return notice
