from accounts.decorators import customer_required, platform_member_required
from core.utils import paginate
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from jobs.services import WorkflowError
from jobs.views import service_model

from .forms import ReviewForm
from .models import Review
from .services import create_review


@platform_member_required
def reviews(request):
    qs = Review.objects.select_related("customer", "worker__user", "booking", "job")
    if request.user.role == "CUSTOMER":
        qs = qs.filter(customer=request.user)
    elif request.user.role == "WORKER":
        qs = qs.filter(worker__user=request.user)
    page = paginate(request, qs)
    return render(
        request,
        "reviews/list.html",
        {"title": "Ratings & reviews", "reviews": page, "page_obj": page},
    )


@customer_required
def create(request, kind, pk):
    model = service_model(kind)
    service = get_object_or_404(model, pk=pk, customer=request.user)
    form = ReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            create_review(
                model, pk, request.user, form.cleaned_data["rating"], form.cleaned_data["text"]
            )
        except WorkflowError as exc:
            form.add_error(None, exc)
        else:
            messages.success(
                request, "Thank you. Your review is now on the professional’s profile."
            )
            return redirect("service_detail", kind=kind, pk=pk)
    return render(
        request,
        "dashboard/form.html",
        {
            "title": "Share your experience",
            "subtitle": service.title,
            "form": form,
            "submit_label": "Publish review",
        },
    )
