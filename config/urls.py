from accounts import views as accounts
from accounts.decorators import platform_member_required
from accounts.forms import (
    StyledPasswordChangeForm,
    StyledPasswordResetForm,
    StyledSetPasswordForm,
)
from adminpanel import views as panel
from complaints import views as complaints
from core import views as core
from customers import views as customers
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from jobs import views as jobs
from notifications import views as notifications
from payments import views as payments
from reviews import views as reviews
from workers import views as workers

urlpatterns = [
    path("", core.home, name="home"),
    path("services/", core.services, name="services"),
    path("about/", core.about, name="about"),
    path("workers/", workers.find_workers, name="find_workers"),
    path("workers/<int:pk>/", workers.worker_detail, name="worker_detail"),
    path("accounts/register/", accounts.register, name="register"),
    path("accounts/login/", accounts.PlatformLoginView.as_view(), name="login"),
    path("accounts/logout/", accounts.logout_view, name="logout"),
    path("accounts/profile/", accounts.profile, name="profile"),
    path("accounts/settings/", accounts.settings_view, name="settings"),
    path(
        "accounts/password/change/",
        platform_member_required(
            auth_views.PasswordChangeView.as_view(
                template_name="accounts/auth_form.html",
                form_class=StyledPasswordChangeForm,
                success_url="/accounts/password/changed/",
            )
        ),
        name="password_change",
    ),
    path(
        "accounts/password/changed/",
        platform_member_required(
            auth_views.PasswordChangeDoneView.as_view(
                template_name="accounts/password_change_done.html"
            )
        ),
        name="password_change_done",
    ),
    path(
        "accounts/password/reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/auth_form.html",
            form_class=StyledPasswordResetForm,
            email_template_name="accounts/password_reset_email.txt",
            subject_template_name="accounts/password_reset_subject.txt",
        ),
        name="password_reset",
    ),
    path(
        "accounts/password/reset/sent/",
        auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "accounts/password/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/auth_form.html", form_class=StyledSetPasswordForm
        ),
        name="password_reset_confirm",
    ),
    path(
        "accounts/password/reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path("dashboard/", accounts.dashboard, name="dashboard"),
    path("customer/dashboard/", customers.dashboard, name="customer_dashboard"),
    path("customer/jobs/", customers.my_jobs, name="customer_jobs"),
    path("customer/jobs/new/", jobs.post_job, name="post_job"),
    path("customer/bookings/", customers.bookings, name="customer_bookings"),
    path("customer/book/<int:pk>/", jobs.book_worker, name="book_worker"),
    path("worker/dashboard/", workers.dashboard, name="worker_dashboard"),
    path("worker/jobs/", workers.my_jobs, name="worker_jobs"),
    path("worker/jobs/available/", workers.available_jobs, name="available_jobs"),
    path("worker/bookings/", workers.bookings, name="worker_bookings"),
    path("worker/profile/", accounts.worker_profile, name="worker_profile"),
    path("worker/availability/", workers.availability, name="availability"),
    path("worker/documents/", workers.documents, name="documents"),
    path("documents/<int:pk>/download/", workers.download_document, name="document_download"),
    path("work/<str:kind>/<int:pk>/", jobs.service_detail, name="service_detail"),
    path("work/<str:kind>/<int:pk>/status/", jobs.transition, name="service_transition"),
    path("payments/", payments.payments, name="payments"),
    path("payments/<int:pk>/", payments.detail, name="payment_detail"),
    path("payments/<int:pk>/status/", payments.update, name="payment_update"),
    path("work/<str:kind>/<int:pk>/pay/", payments.create, name="payment_create"),
    path("reviews/", reviews.reviews, name="reviews"),
    path("work/<str:kind>/<int:pk>/review/", reviews.create, name="review_create"),
    path("notifications/", notifications.notifications, name="notifications"),
    path("notifications/read/", notifications.mark_read, name="notifications_read_all"),
    path("notifications/<int:pk>/read/", notifications.mark_read, name="notification_read"),
    path("complaints/", complaints.complaints, name="complaints"),
    path("complaints/new/", complaints.create, name="complaint_create"),
    path("complaints/<int:pk>/", complaints.detail, name="complaint_detail"),
    path("adminpanel/", panel.dashboard, name="admin_dashboard"),
    path("adminpanel/users/", panel.users, name="admin_users"),
    path("adminpanel/customers/", panel.users, {"role": "CUSTOMER"}, name="admin_customers"),
    path("adminpanel/users/<int:pk>/", panel.user_detail, name="admin_user_detail"),
    path("adminpanel/users/<int:pk>/toggle/", panel.toggle_user, name="toggle_user"),
    path("adminpanel/workers/", panel.workers, name="admin_workers"),
    path("adminpanel/verifications/", panel.workers, {"pending": True}, name="admin_verifications"),
    path("adminpanel/workers/<int:pk>/verify/", panel.verification, name="verify_worker"),
    path("adminpanel/categories/", panel.categories, name="admin_categories"),
    path("adminpanel/categories/new/", panel.category_edit, name="category_create"),
    path("adminpanel/categories/<int:pk>/", panel.category_edit, name="category_edit"),
    path("adminpanel/jobs/", panel.services, {"kind": "job"}, name="admin_jobs"),
    path("adminpanel/bookings/", panel.services, {"kind": "booking"}, name="admin_bookings"),
    path("adminpanel/announcements/", panel.announcements, name="announcements"),
    path("adminpanel/analytics/", panel.analytics, name="analytics"),
    path("django-admin/", admin.site.urls),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
handler403 = "core.views.error403"
handler404 = "core.views.error404"
handler500 = "core.views.error500"
