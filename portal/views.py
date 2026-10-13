from django.utils import timezone
from django.views.generic import TemplateView

from accounts import roles
from accounts.mixins import RoleRequiredMixin
from appointments.models import Appointment
from billing.models import Invoice
from patients.models import Patient


class PortalHomeView(RoleRequiredMixin, TemplateView):
    """Read-only self-service page for patients: profile, appointments, invoices."""

    allowed_roles = (roles.PATIENT,)
    template_name = "portal/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = Patient.objects.filter(user=self.request.user).first()
        context["patient"] = patient
        if patient:
            today = timezone.localdate()
            appointments = patient.appointments.select_related("dentist", "service")
            context["upcoming"] = appointments.filter(
                date__gte=today, status=Appointment.Status.SCHEDULED
            ).order_by("date", "start_time")
            context["past"] = appointments.exclude(
                pk__in=context["upcoming"].values("pk")
            ).order_by("-date", "-start_time")
            context["invoices"] = Invoice.objects.filter(
                appointment__patient=patient
            ).select_related("appointment__service")
        return context
