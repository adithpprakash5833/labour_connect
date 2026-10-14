from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class PlatformUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Platform", {"fields": ("role", "phone", "address", "latitude", "longitude")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Platform", {"fields": ("email", "role", "phone")}),
    )
    list_display = ("username", "email", "role", "is_active")
    list_filter = ("role", "is_active")
