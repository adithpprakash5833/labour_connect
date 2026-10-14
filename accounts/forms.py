from core.forms import LocationFormMixin, StyledFormMixin
from core.models import ServiceCategory
from core.validators import validate_upload
from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.core.exceptions import ValidationError
from django.db import transaction
from workers.models import WorkerDocument, WorkerProfile

from .models import User


class RegistrationForm(StyledFormMixin, LocationFormMixin, UserCreationForm):
    role = forms.ChoiceField(
        choices=[("CUSTOMER", "I am looking for workers"), ("WORKER", "I want to offer services")]
    )
    designation = forms.CharField(max_length=100, required=False)
    category = forms.ModelChoiceField(queryset=ServiceCategory.objects.none(), required=False)
    skills = forms.CharField(
        max_length=400, required=False, help_text="Separate skills with commas."
    )
    experience_years = forms.IntegerField(min_value=0, max_value=70, required=False)
    service_rate = forms.DecimalField(
        min_value=1,
        max_digits=10,
        decimal_places=2,
        required=False,
        label="Hourly service rate (₹)",
    )
    working_area = forms.CharField(max_length=160, required=False)
    availability_status = forms.ChoiceField(
        choices=WorkerProfile.Availability.choices, required=False
    )
    bio = forms.CharField(widget=forms.Textarea, max_length=2000, required=False)
    identity_document = forms.FileField(
        required=False,
        validators=[validate_upload],
        help_text="PDF, PNG or JPEG. Maximum 5 MB. Private to you and administrators.",
    )
    skill_document = forms.FileField(required=False, validators=[validate_upload])

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "role",
            "first_name",
            "last_name",
            "username",
            "email",
            "phone",
            "password1",
            "password2",
            "address",
            "latitude",
            "longitude",
            "profile_photo",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = ServiceCategory.objects.filter(is_active=True)
        for field in ("first_name", "last_name", "email", "phone", "address"):
            self.fields[field].required = True

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        data = super().clean()
        if data.get("role") == "WORKER":
            for name in (
                "designation",
                "category",
                "skills",
                "experience_years",
                "service_rate",
                "working_area",
                "availability_status",
                "bio",
                "identity_document",
                "profile_photo",
            ):
                if data.get(name) in (None, "") and name not in self.errors:
                    self.add_error(name, "This field is required for workers.")
        return data

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data["role"]
        user.save()
        if user.role == "WORKER":
            keys = (
                "designation",
                "category",
                "skills",
                "experience_years",
                "service_rate",
                "working_area",
                "availability_status",
                "bio",
            )
            worker = WorkerProfile.objects.create(
                user=user, **{k: self.cleaned_data[k] for k in keys}
            )
            WorkerDocument.objects.create(
                worker=worker,
                document_type="ID",
                document_file=self.cleaned_data["identity_document"],
            )
            if self.cleaned_data.get("skill_document"):
                WorkerDocument.objects.create(
                    worker=worker,
                    document_type="SKILL",
                    document_file=self.cleaned_data["skill_document"],
                )
        return user


class PlatformAuthenticationForm(StyledFormMixin, AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if user.role == "WORKER":
            profile = getattr(user, "worker_profile", None)
            if not profile or profile.verification_status == "PENDING":
                raise ValidationError(
                    "Your worker profile is awaiting administrator verification. Please return after approval.",
                    code="pending",
                )
            if profile.verification_status != "APPROVED":
                raise ValidationError(
                    "Worker verification rejected: "
                    + (profile.verification_reason or "Contact support for details."),
                    code="rejected",
                )


class UserProfileForm(StyledFormMixin, LocationFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "phone",
            "address",
            "latitude",
            "longitude",
            "profile_photo",
        )


class StyledPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    pass


class StyledPasswordResetForm(StyledFormMixin, PasswordResetForm):
    pass


class StyledSetPasswordForm(StyledFormMixin, SetPasswordForm):
    pass
