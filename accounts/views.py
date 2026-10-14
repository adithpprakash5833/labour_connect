from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from workers.forms import WorkerProfileForm

from .decorators import approved_worker_required, platform_member_required
from .forms import PlatformAuthenticationForm, RegistrationForm, UserProfileForm


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegistrationForm(
        request.POST or None,
        request.FILES or None,
        initial={"role": "WORKER" if request.GET.get("role") == "worker" else "CUSTOMER"},
    )
    if request.method == "POST" and form.is_valid():
        try:
            user = form.save()
        except IntegrityError:
            form.add_error(
                None,
                "An account with these details already exists. Please use another username or email.",
            )
        else:
            if user.role == "WORKER":
                messages.info(
                    request,
                    "Profile submitted. Your worker account is pending verification; sign in after an administrator approves it.",
                )
            else:
                messages.success(request, "Your account is ready. Sign in to find a professional.")
            return redirect("login")
    return render(request, "accounts/register.html", {"form": form, "title": "Create your account"})


class PlatformLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = PlatformAuthenticationForm
    redirect_authenticated_user = True

    def dispatch(self, request, *args, **kwargs):
        self.throttle_key = "login:" + request.META.get("REMOTE_ADDR", "unknown")
        if request.method == "POST" and cache.get(self.throttle_key, 0) >= 15:
            return render(
                request,
                self.template_name,
                {
                    "form": self.authentication_form(request),
                    "throttle_message": "Too many attempts. Please try again in five minutes.",
                },
                status=429,
            )
        return super().dispatch(request, *args, **kwargs)

    def form_invalid(self, form):
        cache.set(self.throttle_key, cache.get(self.throttle_key, 0) + 1, 300)
        return super().form_invalid(form)

    def form_valid(self, form):
        cache.delete(self.throttle_key)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("dashboard")


@platform_member_required
def dashboard(request):
    return redirect(
        {
            "CUSTOMER": "customer_dashboard",
            "WORKER": "worker_dashboard",
            "ADMINISTRATOR": "admin_dashboard",
        }[request.user.role]
    )


@require_POST
def logout_view(request):
    logout(request)
    return redirect("home")


@platform_member_required
def profile(request):
    user_form = UserProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    worker_form = (
        WorkerProfileForm(request.POST or None, instance=request.user.worker_profile)
        if request.user.role == "WORKER"
        else None
    )
    if (
        request.method == "POST"
        and user_form.is_valid()
        and (not worker_form or worker_form.is_valid())
    ):
        with transaction.atomic():
            user_form.save()
            if worker_form:
                worker_form.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("profile")
    return render(
        request,
        "accounts/profile.html",
        {"form": user_form, "worker_form": worker_form, "title": "My profile"},
    )


@approved_worker_required
def worker_profile(request):
    return profile(request)


@platform_member_required
def settings_view(request):
    return render(request, "accounts/settings.html", {"title": "Account settings"})
