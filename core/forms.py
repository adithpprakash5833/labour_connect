from django import forms
from django.core.exceptions import ValidationError


class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs["rows"] = 4
            if name == "address":
                field.widget.attrs["data-address"] = "true"
            if name in ("latitude", "longitude"):
                field.widget.attrs["step"] = "any"


class LocationFormMixin:
    def clean(self):
        data = super().clean()
        if (data.get("latitude") is None) != (data.get("longitude") is None):
            raise ValidationError("Provide both latitude and longitude, or leave both empty.")
        return data
