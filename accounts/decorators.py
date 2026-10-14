from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(role):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(request, *args, **kwargs):
            if request.user.role != role:
                raise PermissionDenied("This page is reserved for a different account role.")
            return view(request, *args, **kwargs)

        return wrapped

    return decorator


customer_required = role_required("CUSTOMER")
admin_required = role_required("ADMINISTRATOR")


def approved_worker_required(view):
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        if request.user.role != "WORKER":
            raise PermissionDenied("A worker account is required.")
        profile = getattr(request.user, "worker_profile", None)
        if not profile or profile.verification_status != "APPROVED":
            raise PermissionDenied("Worker verification must be approved to access this page.")
        return view(request, *args, **kwargs)

    return wrapped


def platform_member_required(view):
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        if request.user.role == "WORKER":
            profile = getattr(request.user, "worker_profile", None)
            if not profile or profile.verification_status != "APPROVED":
                raise PermissionDenied("Worker approval is required.")
        return view(request, *args, **kwargs)

    return wrapped
