from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts import roles
from accounts.mixins import PageContextMixin, RoleRequiredMixin, SafeDeleteMixin

from .forms import ServiceForm
from .models import Service


class ServiceListView(RoleRequiredMixin, ListView):
    allowed_roles = roles.STAFF
    model = Service
    template_name = "services/service_list.html"
    context_object_name = "services"

    def get_queryset(self):
        queryset = super().get_queryset()
        # Only the manager needs to see retired services.
        if not self.request.user.is_clinic_admin:
            queryset = queryset.filter(is_active=True)
        return queryset


class ServiceCreateView(RoleRequiredMixin, PageContextMixin, SuccessMessageMixin, CreateView):
    allowed_roles = (roles.ADMIN,)
    model = Service
    form_class = ServiceForm
    template_name = "form_page.html"
    success_url = reverse_lazy("services:list")
    success_message = _("Service created.")
    page_title = _("Add service")
    cancel_url = reverse_lazy("services:list")


class ServiceUpdateView(RoleRequiredMixin, PageContextMixin, SuccessMessageMixin, UpdateView):
    allowed_roles = (roles.ADMIN,)
    model = Service
    form_class = ServiceForm
    template_name = "form_page.html"
    success_url = reverse_lazy("services:list")
    success_message = _("Service updated.")
    page_title = _("Edit service")
    cancel_url = reverse_lazy("services:list")


class ServiceDeleteView(
    RoleRequiredMixin, PageContextMixin, SafeDeleteMixin, SuccessMessageMixin, DeleteView
):
    allowed_roles = (roles.ADMIN,)
    model = Service
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("services:list")
    success_message = _("Service deleted.")
    page_title = _("Delete service")
    cancel_url = reverse_lazy("services:list")
