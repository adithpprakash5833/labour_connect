from core.forms import StyledFormMixin
from core.models import ServiceCategory
from django import forms

from .models import Announcement


class CategoryForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ServiceCategory
        fields = ("name", "slug", "description", "icon", "image", "is_active")


class VerificationForm(StyledFormMixin, forms.Form):
    status = forms.ChoiceField(
        choices=[("APPROVED", "Approve"), ("REJECTED", "Reject"), ("PENDING", "Return to pending")]
    )
    reason = forms.CharField(widget=forms.Textarea, required=False, max_length=3000)

    def clean(self):
        data = super().clean()
        if data.get("status") == "REJECTED" and not data.get("reason"):
            self.add_error("reason", "A rejection reason is required.")
        return data


class AnnouncementForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ("title", "message", "audience")
