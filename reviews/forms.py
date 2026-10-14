from core.forms import StyledFormMixin
from django import forms

from .models import Review


class ReviewForm(StyledFormMixin, forms.ModelForm):
    rating = forms.TypedChoiceField(
        choices=[
            (
                i,
                f"{i} — "
                + (
                    "Excellent"
                    if i == 5
                    else "Good"
                    if i == 4
                    else "Average"
                    if i == 3
                    else "Fair"
                    if i == 2
                    else "Poor"
                ),
            )
            for i in range(5, 0, -1)
        ],
        coerce=int,
    )

    class Meta:
        model = Review
        fields = ("rating", "text")
