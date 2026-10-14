import math
from decimal import Decimal, InvalidOperation

from django.db.models import Avg, Count, Q, Value
from django.db.models.functions import Concat

from .models import WorkerProfile


def number(value, low=None, high=None):
    try:
        result = Decimal(value)
        if (
            not result.is_finite()
            or (low is not None and result < low)
            or (high is not None and result > high)
        ):
            return None
        return result
    except (InvalidOperation, TypeError, ValueError):
        return None


def haversine(lat1, lng1, lat2, lng2):
    a, b, c, d = map(math.radians, map(float, (lat1, lng1, lat2, lng2)))
    h = math.sin((c - a) / 2) ** 2 + math.cos(a) * math.cos(c) * math.sin((d - b) / 2) ** 2
    return round(6371 * 2 * math.asin(math.sqrt(min(1, h))), 1)


def search_workers(params):
    qs = (
        WorkerProfile.objects.filter(
            user__is_active=True, verification_status="APPROVED", category__is_active=True
        )
        .select_related("user", "category")
        .annotate(
            rating=Avg("reviews__rating"),
            review_count=Count("reviews", distinct=True),
            full_name=Concat("user__first_name", Value(" "), "user__last_name"),
        )
    )
    term = params.get("q", "").strip()
    if term:
        qs = qs.filter(
            Q(user__first_name__icontains=term)
            | Q(full_name__icontains=term)
            | Q(user__username__icontains=term)
            | Q(user__last_name__icontains=term)
            | Q(designation__icontains=term)
            | Q(skills__icontains=term)
            | Q(category__name__icontains=term)
            | Q(bio__icontains=term)
        )
    if params.get("category"):
        qs = qs.filter(category__slug=params["category"])
    if params.get("location"):
        qs = qs.filter(
            Q(working_area__icontains=params["location"])
            | Q(user__address__icontains=params["location"])
        )
    for key, lookup, low, high in [
        ("experience", "experience_years__gte", 0, 70),
        ("rating", "rating__gte", 0, 5),
        ("min_price", "service_rate__gte", 0, None),
        ("max_price", "service_rate__lte", 0, None),
    ]:
        value = number(params.get(key), low, high)
        if value is not None:
            qs = qs.filter(**{lookup: value})
    if params.get("availability") in WorkerProfile.Availability.values:
        qs = qs.filter(availability_status=params["availability"])
    sort = params.get("sort", "recommended")
    orders = {
        "recommended": ["-rating", "-experience_years", "pk"],
        "rating": ["-rating", "pk"],
        "experience": ["-experience_years", "pk"],
        "price_low": ["service_rate", "pk"],
        "price_high": ["-service_rate", "pk"],
    }
    qs = qs.order_by(*orders.get(sort, orders["recommended"]))
    lat = number(params.get("latitude"), -90, 90)
    lng = number(params.get("longitude"), -180, 180)
    if lat is not None and lng is not None:
        results = list(qs)
        for worker in results:
            worker.distance = (
                haversine(lat, lng, worker.user.latitude, worker.user.longitude)
                if worker.user.latitude is not None and worker.user.longitude is not None
                else None
            )
        if sort == "nearest":
            results.sort(
                key=lambda w: (
                    w.distance is None,
                    w.distance if w.distance is not None else math.inf,
                )
            )
        return results
    return qs
