import calendar
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.http import urlencode
from django.utils.translation import gettext as _, gettext_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts import roles
from accounts.mixins import PageContextMixin, RoleRequiredMixin, SafeDeleteMixin
from accounts.models import User

from .forms import AppointmentForm
from .models import Appointment


def parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return timezone.localdate()


def calendar_window(mode, anchor):
    """Return (start, end, previous_anchor, next_anchor) for day/week/month views."""
    if mode == "week":
        start = anchor - timedelta(days=anchor.weekday())  # Monday
        return start, start + timedelta(days=6), anchor - timedelta(days=7), anchor + timedelta(days=7)
    if mode == "month":
        start = anchor.replace(day=1)
        end = anchor.replace(day=calendar.monthrange(anchor.year, anchor.month)[1])
        return start, end, (start - timedelta(days=1)).replace(day=1), end + timedelta(days=1)
    return anchor, anchor, anchor - timedelta(days=1), anchor + timedelta(days=1)


class AppointmentListView(RoleRequiredMixin, ListView):
    """Day / week / month agenda. Dentists only ever see their own appointments."""

    allowed_roles = roles.STAFF
    template_name = "appointments/appointment_list.html"
    context_object_name = "appointments"

    def _mode(self):
        mode = self.request.GET.get("view", "day")
        return mode if mode in ("day", "week", "month") else "day"

    def get_queryset(self):
        start, end, _, _ = calendar_window(self._mode(), parse_date(self.request.GET.get("date")))
        queryset = (
            Appointment.objects.visible_to(self.request.user)
            .select_related("patient", "dentist", "service")
            .filter(date__range=(start, end))
        )
        params = self.request.GET
        if params.get("status") in Appointment.Status.values:
            queryset = queryset.filter(status=params["status"])
        if params.get("dentist", "").isdigit() and not self.request.user.is_dentist:
            queryset = queryset.filter(dentist_id=params["dentist"])
        for term in params.get("q", "").split():
            queryset = queryset.filter(
                Q(patient__first_name__icontains=term) | Q(patient__last_name__icontains=term)
            )
        return queryset.order_by("date", "start_time")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mode = self._mode()
        anchor = parse_date(self.request.GET.get("date"))
        start, end, prev_date, next_date = calendar_window(mode, anchor)
        filters = {k: v for k, v in self.request.GET.items() if k in ("status", "dentist", "q") and v}
        context.update(
            mode=mode,
            anchor=anchor,
            range_start=start,
            range_end=end,
            prev_date=prev_date,
            next_date=next_date,
            today=timezone.localdate(),
            filter_query=urlencode(filters),
            status_choices=Appointment.Status.choices,
            dentists=User.objects.filter(role=roles.DENTIST, is_active=True),
            selected_status=self.request.GET.get("status", ""),
            selected_dentist=self.request.GET.get("dentist", ""),
            q=self.request.GET.get("q", ""),
        )
        return context


class AppointmentDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = roles.STAFF
    template_name = "appointments/appointment_detail.html"
    context_object_name = "appointment"

    def get_queryset(self):
        return Appointment.objects.visible_to(self.request.user).select_related(
            "patient", "dentist", "service"
        )


class _AppointmentSaveMixin:
    """Turn a late (race-condition) double-booking into a normal form error."""

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)
        messages.success(self.request, self.success_message)
        return response


class AppointmentCreateView(
    RoleRequiredMixin, PageContextMixin, _AppointmentSaveMixin, CreateView
):
    allowed_roles = roles.FRONT_DESK
    model = Appointment
    form_class = AppointmentForm
    template_name = "form_page.html"
    success_message = gettext_lazy("Appointment booked.")
    page_title = gettext_lazy("Book appointment")
    cancel_url = reverse_lazy("appointments:list")

    def get_initial(self):
        initial = super().get_initial()
        patient = self.request.GET.get("patient", "")
        if patient.isdigit():
            initial["patient"] = patient
        if self.request.GET.get("date"):
            initial["date"] = parse_date(self.request.GET["date"])
        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class AppointmentUpdateView(
    RoleRequiredMixin, PageContextMixin, _AppointmentSaveMixin, UpdateView
):
    allowed_roles = roles.FRONT_DESK
    model = Appointment
    form_class = AppointmentForm
    template_name = "form_page.html"
    success_message = gettext_lazy("Appointment updated.")
    page_title = gettext_lazy("Edit appointment")

    def get_cancel_url(self):
        return self.object.get_absolute_url()


class AppointmentStatusView(RoleRequiredMixin, View):
    """POST-only: change status (cancel, complete, no-show, re-schedule)."""

    allowed_roles = roles.STAFF
    dentist_statuses = (
        Appointment.Status.SCHEDULED,
        Appointment.Status.COMPLETED,
        Appointment.Status.NO_SHOW,
    )

    def post(self, request, pk):
        appointment = get_object_or_404(Appointment.objects.visible_to(request.user), pk=pk)
        new_status = request.POST.get("status")
        permitted = Appointment.Status.values if request.user.is_front_desk else self.dentist_statuses
        if new_status not in Appointment.Status.values or new_status not in permitted:
            messages.error(request, _("You cannot set that status."))
            return redirect(appointment)
        appointment.status = new_status
        try:
            appointment.save(update_fields=["status", "updated_at"])
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        else:
            messages.success(
                request,
                _("Appointment marked as %(status)s.")
                % {"status": appointment.get_status_display().lower()},
            )
        return redirect(appointment)


class AppointmentDeleteView(
    RoleRequiredMixin, PageContextMixin, SafeDeleteMixin, SuccessMessageMixin, DeleteView
):
    allowed_roles = (roles.ADMIN,)
    model = Appointment
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("appointments:list")
    success_message = gettext_lazy("Appointment deleted.")
    page_title = gettext_lazy("Delete appointment")

    def get_cancel_url(self):
        return self.object.get_absolute_url()
