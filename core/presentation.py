from django.urls import reverse


def service_rows(items):
    return [
        {
            "cells": [
                s.title,
                s.category.name,
                s.customer.display_name,
                s.worker.user.display_name if s.worker_id else "Unassigned",
                s.job_date.strftime("%d %b %Y"),
                f"₹{s.budget:,.2f}",
            ],
            "status": s.status,
            "url": reverse("service_detail", args=[s.kind, s.pk]),
        }
        for s in items
    ]


def payment_rows(items):
    return [
        {
            "cells": [
                p.service.title,
                p.customer.display_name,
                p.worker.user.display_name,
                f"₹{p.amount:,.2f}",
                p.get_payment_method_display(),
                p.created_at.strftime("%d %b %Y"),
            ],
            "status": p.payment_status,
            "url": reverse("payment_detail", args=[p.pk]),
        }
        for p in items
    ]


SERVICE_COLUMNS = ["Service", "Category", "Customer", "Professional", "Scheduled", "Budget"]
PAYMENT_COLUMNS = ["Service", "Customer", "Professional", "Amount", "Method", "Recorded"]
