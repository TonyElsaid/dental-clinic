from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from accounts import roles
from accounts.mixins import PageContextMixin, QueryStringMixin, RoleRequiredMixin
from appointments.models import Appointment

from .forms import PaymentForm
from .models import Invoice
from .pdf import render_invoice_pdf


class InvoiceListView(RoleRequiredMixin, QueryStringMixin, ListView):
    allowed_roles = roles.FRONT_DESK
    template_name = "billing/invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 15

    def get_queryset(self):
        queryset = Invoice.objects.select_related(
            "appointment__patient", "appointment__service", "appointment__dentist"
        )
        status = self.request.GET.get("status")
        if status in Invoice.Status.values:
            queryset = queryset.filter(status=status)
        for term in self.request.GET.get("q", "").split():
            queryset = queryset.filter(
                Q(invoice_number__icontains=term)
                | Q(appointment__patient__first_name__icontains=term)
                | Q(appointment__patient__last_name__icontains=term)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        outstanding = Invoice.objects.exclude(status=Invoice.Status.PAID).aggregate(
            billed=Sum("amount"), paid=Sum("amount_paid")
        )
        context.update(
            status_choices=Invoice.Status.choices,
            selected_status=self.request.GET.get("status", ""),
            q=self.request.GET.get("q", ""),
            outstanding_total=(outstanding["billed"] or 0) - (outstanding["paid"] or 0),
        )
        return context


class InvoiceDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = roles.FRONT_DESK
    template_name = "billing/invoice_detail.html"
    context_object_name = "invoice"

    def get_queryset(self):
        return Invoice.objects.select_related(
            "appointment__patient", "appointment__service", "appointment__dentist"
        ).prefetch_related("payments")


class InvoiceCreateView(RoleRequiredMixin, View):
    """POST-only: create the invoice for a completed appointment."""

    allowed_roles = roles.FRONT_DESK

    def post(self, request, appointment_pk):
        appointment = get_object_or_404(Appointment.objects.select_related("service"), pk=appointment_pk)
        if appointment.status != Appointment.Status.COMPLETED:
            messages.error(request, "Invoices can only be generated for completed appointments.")
            return redirect(appointment)
        invoice, created = Invoice.objects.get_or_create(
            appointment=appointment, defaults={"amount": appointment.service.price}
        )
        if created:
            messages.success(request, f"Invoice {invoice.invoice_number} generated.")
        else:
            messages.info(request, "An invoice already exists for this appointment.")
        return redirect(invoice)


class PaymentCreateView(RoleRequiredMixin, PageContextMixin, CreateView):
    allowed_roles = roles.FRONT_DESK
    form_class = PaymentForm
    template_name = "form_page.html"
    submit_label = "Record payment"

    def dispatch(self, request, *args, **kwargs):
        self.invoice = get_object_or_404(Invoice, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if self.invoice.status == Invoice.Status.PAID:
            messages.info(request, "This invoice is already fully paid.")
            return redirect(self.invoice)
        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["invoice"] = self.invoice
        return kwargs

    @property
    def page_title(self):
        return f"Record payment for {self.invoice.invoice_number} (balance ${self.invoice.balance})"

    def get_cancel_url(self):
        return self.invoice.get_absolute_url()

    def form_valid(self, form):
        form.instance.invoice = self.invoice
        response = super().form_valid(form)
        messages.success(self.request, "Payment recorded.")
        return response

    def get_success_url(self):
        return reverse("billing:detail", args=[self.invoice.pk])


class InvoicePDFView(LoginRequiredMixin, View):
    """Front desk may download any invoice; patients only their own."""

    def get(self, request, pk):
        invoice = get_object_or_404(
            Invoice.objects.select_related(
                "appointment__patient", "appointment__service", "appointment__dentist"
            ),
            pk=pk,
        )
        user = request.user
        allowed = user.is_front_desk or (
            user.is_patient_user and invoice.appointment.patient.user_id == user.pk
        )
        if not allowed:
            raise PermissionDenied
        response = HttpResponse(render_invoice_pdf(invoice), content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{invoice.invoice_number}.pdf"'
        return response
