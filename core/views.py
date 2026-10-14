from django.db.models import Avg, Count
from django.shortcuts import render
from jobs.models import Booking, Job
from reviews.models import Review
from workers.models import WorkerProfile

from .models import ServiceCategory


def home(request):
    workers = (
        WorkerProfile.objects.filter(
            user__is_active=True, verification_status="APPROVED", category__is_active=True
        )
        .select_related("user", "category")
        .annotate(rating=Avg("reviews__rating"), review_count=Count("reviews", distinct=True))
        .order_by("-rating", "-experience_years")[:4]
    )
    return render(
        request,
        "public/home.html",
        {
            "categories": ServiceCategory.objects.filter(is_active=True)
            .annotate(
                activity=Count("booking_services", distinct=True)
                + Count("job_services", distinct=True)
            )
            .order_by("-activity", "name"),
            "workers": workers,
            "testimonials": Review.objects.filter(
                worker__verification_status="APPROVED",
                worker__user__is_active=True,
                worker__category__is_active=True,
            ).select_related("customer", "worker__category")[:3],
            "stats": {
                "workers": WorkerProfile.objects.filter(
                    user__is_active=True, verification_status="APPROVED"
                ).count(),
                "categories": ServiceCategory.objects.filter(is_active=True).count(),
                "completed": Job.objects.filter(status="COMPLETED").count()
                + Booking.objects.filter(status="COMPLETED").count(),
            },
        },
    )


def services(request):
    return render(
        request,
        "public/services.html",
        {"categories": ServiceCategory.objects.filter(is_active=True)},
    )


def about(request):
    return render(request, "public/about.html")


def error_page(request, exception=None, code=404):
    return render(request, "errors/error.html", {"code": code}, status=code)


def error403(request, exception):
    return error_page(request, exception, 403)


def error404(request, exception):
    return error_page(request, exception, 404)


def error500(request):
    return error_page(request, code=500)
