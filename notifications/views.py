from accounts.decorators import platform_member_required
from core.utils import paginate
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST


@platform_member_required
def notifications(request):
    qs = request.user.notifications.all()
    if request.GET.get("unread") == "1":
        qs = qs.filter(is_read=False)
    page = paginate(request, qs)
    return render(
        request,
        "notifications/list.html",
        {"title": "Your notifications", "notifications": page, "page_obj": page},
    )


@require_POST
@platform_member_required
def mark_read(request, pk=None):
    qs = request.user.notifications.filter(is_read=False)
    if pk:
        item = get_object_or_404(request.user.notifications, pk=pk)
        item.is_read = True
        item.save(update_fields=["is_read"])
    else:
        qs.update(is_read=True)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse(
            {"ok": True, "unread": request.user.notifications.filter(is_read=False).count()}
        )
    messages.success(request, "Notifications marked as read.")
    return redirect("notifications")
