from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, UpdateView

from accounts import roles
from accounts.mixins import (
    PageContextMixin,
    QueryStringMixin,
    RoleRequiredMixin,
    SafeDeleteMixin,
)

from .forms import PatientForm, PortalAccountForm
from .models import Patient


class PatientListView(RoleRequiredMixin, QueryStringMixin, ListView):
    allowed_roles = roles.STAFF
    template_name = "patients/patient_list.html"
    context_object_name = "patients"
    paginate_by = 15

    def get_queryset(self):
        queryset = Patient.objects.visible_to(self.request.user)
        queryset = queryset.search(self.request.GET.get("q"))
        gender = self.request.GET.get("gender")
        if gender in Patient.Gender.values:
            queryset = queryset.filter(gender=gender)
        if self.request.GET.get("allergies") == "yes":
            queryset = queryset.exclude(allergies="")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["genders"] = Patient.Gender.choices
        context["q"] = self.request.GET.get("q", "")
        context["selected_gender"] = self.request.GET.get("gender", "")
        context["allergies_only"] = self.request.GET.get("allergies") == "yes"
        return context


class PatientDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = roles.STAFF
    template_name = "patients/patient_detail.html"
    context_object_name = "patient"

    def get_queryset(self):
        return Patient.objects.visible_to(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        appointments = self.object.appointments.select_related("dentist", "service")
        if self.request.user.is_dentist:  # dentists only see their own appointments
            appointments = appointments.filter(dentist=self.request.user)
        context["appointments"] = appointments.order_by("-date", "-start_time")
        return context


class PatientCreateView(RoleRequiredMixin, PageContextMixin, SuccessMessageMixin, CreateView):
    allowed_roles = roles.FRONT_DESK
    model = Patient
    form_class = PatientForm
    template_name = "form_page.html"
    success_message = _("Patient registered.")
    page_title = _("Register patient")
    cancel_url = reverse_lazy("patients:list")


class PatientUpdateView(RoleRequiredMixin, PageContextMixin, SuccessMessageMixin, UpdateView):
    allowed_roles = roles.FRONT_DESK
    model = Patient
    form_class = PatientForm
    template_name = "form_page.html"
    success_message = _("Patient updated.")
    page_title = _("Edit patient")

    def get_cancel_url(self):
        return self.object.get_absolute_url()


class PatientDeleteView(
    RoleRequiredMixin, PageContextMixin, SafeDeleteMixin, SuccessMessageMixin, DeleteView
):
    allowed_roles = (roles.ADMIN,)
    model = Patient
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("patients:list")
    success_message = _("Patient deleted.")
    page_title = _("Delete patient")

    def get_cancel_url(self):
        return reverse("patients:detail", args=[self.object.pk])


class PortalAccountCreateView(RoleRequiredMixin, PageContextMixin, FormView):
    """Front desk creates a patient-portal login for a patient."""

    allowed_roles = roles.FRONT_DESK
    form_class = PortalAccountForm
    template_name = "form_page.html"
    submit_label = _("Create account")
    page_title = _("Create patient portal account")

    def dispatch(self, request, *args, **kwargs):
        self.patient = get_object_or_404(Patient, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if self.patient.user_id:
            messages.info(request, _("This patient already has a portal account."))
            return redirect(self.patient)
        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["patient"] = self.patient
        return kwargs

    def get_cancel_url(self):
        return self.patient.get_absolute_url()

    def form_valid(self, form):
        if self.patient.user_id:
            messages.error(self.request, _("This patient already has a portal account."))
            return redirect(self.patient)
        form.save()
        messages.success(self.request, _("Portal account created."))
        return redirect(self.patient)
