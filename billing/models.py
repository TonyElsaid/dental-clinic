from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone


class Invoice(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PARTIAL = "partial", "Partial"
        PAID = "paid", "Paid"

    appointment = models.OneToOneField(
        "appointments.Appointment", on_delete=models.PROTECT, related_name="invoice"
    )
    # NULL (not '') while unsaved so the unique constraint never collides.
    invoice_number = models.CharField(max_length=20, unique=True, null=True, blank=True, editable=False)
    issue_date = models.DateField(default=timezone.localdate)
    # Snapshot of the service price at invoicing time, so later price changes
    # do not rewrite history.
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), editable=False)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, editable=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-issue_date", "-id"]

    def __str__(self):
        return self.invoice_number or f"Invoice (appointment {self.appointment_id})"

    def get_absolute_url(self):
        return reverse("billing:detail", args=[self.pk])

    @property
    def patient(self):
        return self.appointment.patient

    @property
    def balance(self):
        return self.amount - self.amount_paid

    def save(self, *args, **kwargs):
        with transaction.atomic():
            super().save(*args, **kwargs)
            if not self.invoice_number:
                self.invoice_number = f"INV-{self.issue_date.year}-{self.pk:05d}"
                super().save(update_fields=["invoice_number"])

    def recalculate(self):
        """Derive paid amount and status from the recorded payments."""
        total = self.payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        self.amount_paid = total
        if total >= self.amount:
            self.status = self.Status.PAID
        elif total > 0:
            self.status = self.Status.PARTIAL
        else:
            self.status = self.Status.PENDING
        self.save(update_fields=["amount_paid", "status"])


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        CARD = "card", "Card"
        TRANSFER = "transfer", "Bank transfer"
        INSURANCE = "insurance", "Insurance"

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    method = models.CharField(max_length=20, choices=Method.choices, default=Method.CASH)
    paid_at = models.DateTimeField(default=timezone.now)
    reference = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["paid_at"]

    def __str__(self):
        return f"{self.amount} on {self.paid_at:%Y-%m-%d}"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            super().save(*args, **kwargs)
            self.invoice.recalculate()

    def delete(self, *args, **kwargs):
        invoice = self.invoice
        with transaction.atomic():
            result = super().delete(*args, **kwargs)
            invoice.recalculate()
        return result
