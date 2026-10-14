from core.forms import LocationFormMixin, StyledFormMixin
from core.models import ServiceCategory
from django import forms
from django.utils import timezone

from .models import Booking, Job


class ServiceForm(StyledFormMixin, LocationFormMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "category" in self.fields:
            self.fields["category"].queryset = ServiceCategory.objects.filter(is_active=True)
        self.fields["job_date"].widget = forms.DateInput(
            attrs={"type": "date", "class": "form-control"}
        )
        self.fields["preferred_time"].widget = forms.TimeInput(
            attrs={"type": "time", "class": "form-control"}
        )
        self.fields["budget"].label = "Agreed budget (₹)"

    def clean_job_date(self):
        date = self.cleaned_data["job_date"]
        if date < timezone.localdate():
            raise forms.ValidationError("Choose today or a future date.")
        return date


class BookingForm(ServiceForm):
    class Meta:
        model = Booking
        fields = (
            "title",
            "description",
            "job_date",
            "preferred_time",
            "budget",
            "address",
            "latitude",
            "longitude",
            "urgent",
            "special_instructions",
        )


class JobForm(ServiceForm):
    class Meta:
        model = Job
        fields = (
            "title",
            "description",
            "category",
            "required_skill",
            "budget",
            "job_date",
            "preferred_time",
            "address",
            "latitude",
            "longitude",
            "urgent",
        )


class TransitionForm(forms.Form):
    target = forms.ChoiceField(
        choices=[(x, x) for x in ("ACCEPTED", "REJECTED", "IN_PROGRESS", "COMPLETED", "CANCELLED")]
    )
