from django import forms

from accounts.mixins import BootstrapFormMixin

from .models import Payment


class PaymentForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["amount", "method", "reference"]

    def __init__(self, *args, invoice=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.invoice = invoice
        if invoice is not None:
            self.fields["amount"].initial = invoice.balance
            self.fields["amount"].widget.attrs.update({"step": "0.01", "min": "0.01"})

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if self.invoice is not None and amount > self.invoice.balance:
            raise forms.ValidationError(
                f"Payment exceeds the outstanding balance of ${self.invoice.balance}."
            )
        return amount
