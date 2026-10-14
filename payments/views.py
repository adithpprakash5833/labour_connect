from accounts.decorators import customer_required, platform_member_required
from core.presentation import PAYMENT_COLUMNS, payment_rows
from core.utils import paginate
from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from jobs.services import WorkflowError
from jobs.views import service_model

from .forms import PaymentForm
from .models import Payment
from .services import change_payment, record_payment


def scoped_payments(user):
    qs = Payment.objects.select_related("customer", "worker__user", "booking", "job")
    if user.role == "CUSTOMER":
        return qs.filter(customer=user)
    if user.role == "WORKER":
        return qs.filter(worker__user=user)
    return qs


@platform_member_required
def payments(request):
    qs = scoped_payments(request.user)
    if request.GET.get("status"):
        qs = qs.filter(payment_status=request.GET["status"])
    page = paginate(request, qs)
    total = (
        scoped_payments(request.user)
        .filter(payment_status="PAID")
        .aggregate(total=Sum("amount"))["total"]
        or 0
    )
    return render(
        request,
        "dashboard/records.html",
        {
            "title": "Earnings" if request.user.role == "WORKER" else "Payment history",
            "subtitle": f"Confirmed paid records: ₹{total:,.2f}. Demo records are simulated; this platform does not transfer money.",
            "rows": payment_rows(page),
            "columns": PAYMENT_COLUMNS,
            "page_obj": page,
            "payment_filter": True,
        },
    )


@customer_required
def create(request, kind, pk):
    model = service_model(kind)
    service = get_object_or_404(model, pk=pk, customer=request.user)
    form = PaymentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            payment = record_payment(
                model,
                pk,
                request.user,
                form.cleaned_data["payment_method"],
                form.cleaned_data["transaction_reference"],
            )
        except WorkflowError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Payment record created.")
            return redirect("payment_detail", pk=payment.pk)
    return render(
        request,
        "dashboard/form.html",
        {
            "title": "Record a payment",
            "subtitle": f"{service.title} · Agreed amount ₹{service.budget}. Cash/UPI records need worker confirmation. Demo online payments are simulated and move no money.",
            "form": form,
            "submit_label": "Create payment record",
        },
    )


@platform_member_required
def detail(request, pk):
    payment = get_object_or_404(scoped_payments(request.user), pk=pk)
    can_confirm = (
        request.user.role in ("WORKER", "ADMINISTRATOR") and payment.payment_status == "PENDING"
    )
    return render(
        request,
        "payments/detail.html",
        {
            "title": "Payment receipt",
            "payment": payment,
            "can_confirm": can_confirm,
            "can_refund": request.user.role == "ADMINISTRATOR" and payment.payment_status == "PAID",
        },
    )


@require_POST
@platform_member_required
def update(request, pk):
    get_object_or_404(scoped_payments(request.user), pk=pk)
    try:
        change_payment(pk, request.user, request.POST.get("target"))
    except WorkflowError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        messages.success(request, "Payment status updated.")
    return redirect("payment_detail", pk=pk)
