from django.contrib import admin

from .models import Invoice, Payment


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "appointment", "amount", "amount_paid", "status", "issue_date")
    list_filter = ("status",)
    readonly_fields = ("invoice_number", "amount_paid", "status")
    inlines = [PaymentInline]
