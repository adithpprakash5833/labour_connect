from core.forms import StyledFormMixin
from django import forms
from django.db.models import Q
from jobs.models import Booking, Job

from .models import Complaint


class ComplaintForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ("subject", "description", "related_job", "related_booking")

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        scope = Q(customer=user) if user.role == "CUSTOMER" else Q(worker__user=user)
        self.fields["related_job"].queryset = Job.objects.filter(scope)
        self.fields["related_booking"].queryset = Booking.objects.filter(scope)

    def clean(self):
        data = super().clean()
        if data.get("related_job") and data.get("related_booking"):
            raise forms.ValidationError("Choose a job or a booking, not both.")
        return data


class ComplaintResponseForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ("status", "admin_response")

    def clean(self):
        data = super().clean()
        if data.get("status") in ("RESOLVED", "CLOSED") and not data.get("admin_response"):
            self.add_error(
                "admin_response", "Include a response when resolving or closing a complaint."
            )
        return data
