from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView

from appointments.models import Appointment
from billing.models import Invoice
from patients.models import Patient


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_patient_user:
            return redirect("portal:home")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.localdate()

        # visible_to() makes every figure role-aware: dentists only see their own.
        appointments = Appointment.objects.visible_to(user).select_related(
            "patient", "dentist", "service"
        )
        patients = Patient.objects.visible_to(user)

        context.update(
            today=today,
            today_appointments=appointments.filter(date=today).order_by("start_time"),
            upcoming_count=appointments.filter(
                date__gt=today, status=Appointment.Status.SCHEDULED
            ).count(),
            month_appointments=appointments.filter(
                date__year=today.year, date__month=today.month
            ).count(),
            total_patients=patients.count(),
            recent_patients=patients.order_by("-created_at")[:5],
        )
        if user.is_front_desk:
            unpaid = Invoice.objects.exclude(status=Invoice.Status.PAID)
            totals = unpaid.aggregate(billed=Sum("amount"), paid=Sum("amount_paid"))
            context["unpaid_invoices"] = unpaid.count()
            context["outstanding_total"] = (totals["billed"] or 0) - (totals["paid"] or 0)
        return context
