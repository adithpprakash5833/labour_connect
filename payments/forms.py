from core.forms import StyledFormMixin
from django import forms

from .models import Payment


class PaymentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Payment
        fields = ("payment_method", "transaction_reference")

    def clean(self):
        data = super().clean()
        if data.get("payment_method") == "UPI" and not data.get("transaction_reference"):
            self.add_error(
                "transaction_reference", "Enter the reference from your actual UPI payment."
            )
        return data
