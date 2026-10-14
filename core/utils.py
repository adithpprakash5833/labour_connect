from datetime import datetime, time
from datetime import timezone as datetime_timezone

from django.core.paginator import Paginator
from django.db.models import Count, DateTimeField, F, Func, Sum, Value
from django.db.models.functions import TruncMonth
from django.utils import timezone


def paginate(request, queryset, per_page=12):
    return Paginator(queryset, per_page).get_page(request.GET.get("page"))


def monthly_series(queryset, sum_field=None, date_field="created_at"):
    now = timezone.localdate()
    months = []
    for back in range(5, -1, -1):
        ordinal = now.year * 12 + now.month - 1 - back
        months.append((ordinal // 12, ordinal % 12 + 1))
    first_year, first_month = months[0]
    aggregate = Sum(sum_field) if sum_field else Count("pk")
    boundary = timezone.make_aware(
        datetime.combine(now.replace(year=first_year, month=first_month, day=1), time.min)
    )
    # Explicit offsets keep Indian local-month charts correct even on MySQL
    # installations without the optional named timezone tables.
    local_time = Func(
        F(date_field),
        Value("+00:00"),
        Value("+05:30"),
        function="CONVERT_TZ",
        output_field=DateTimeField(),
    )
    records = (
        queryset.filter(**{f"{date_field}__gte": boundary})
        .annotate(month=TruncMonth(local_time, tzinfo=datetime_timezone.utc))
        .values("month")
        .annotate(value=aggregate)
    )
    values = {(r["month"].year, r["month"].month): float(r["value"] or 0) for r in records}
    return {
        "labels": [timezone.datetime(y, m, 1).strftime("%b %Y") for y, m in months],
        "values": [values.get((y, m), 0) for y, m in months],
    }


def status_series(queryset):
    rows = list(queryset.values("status").annotate(value=Count("pk")).order_by("status"))
    return {
        "labels": [r["status"].replace("_", " ").title() for r in rows],
        "values": [r["value"] for r in rows],
    }
