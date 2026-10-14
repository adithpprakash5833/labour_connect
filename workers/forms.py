from core.forms import StyledFormMixin
from core.models import ServiceCategory
from django import forms

from .models import WorkerDocument, WorkerProfile


class WorkerProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = WorkerProfile
        fields = (
            "designation",
            "category",
            "skills",
            "experience_years",
            "service_rate",
            "working_area",
            "bio",
            "availability_status",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = ServiceCategory.objects.filter(is_active=True)


class DocumentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = WorkerDocument
        fields = ("document_type", "document_file")


class AvailabilityForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = WorkerProfile
        fields = ("availability_status",)
