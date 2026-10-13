from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, ListView

from . import roles
from .forms import StaffCreateForm
from .mixins import PageContextMixin, RoleRequiredMixin
from .models import User


class StaffListView(RoleRequiredMixin, ListView):
    allowed_roles = (roles.ADMIN,)
    template_name = "accounts/staff_list.html"
    context_object_name = "staff"

    def get_queryset(self):
        return User.objects.exclude(role=roles.PATIENT).order_by("role", "last_name", "username")


class StaffCreateView(RoleRequiredMixin, PageContextMixin, SuccessMessageMixin, CreateView):
    allowed_roles = (roles.ADMIN,)
    form_class = StaffCreateForm
    template_name = "form_page.html"
    success_url = reverse_lazy("accounts:staff_list")
    success_message = _("Staff account created.")
    page_title = _("Add staff member")
    cancel_url = reverse_lazy("accounts:staff_list")


class StaffToggleActiveView(RoleRequiredMixin, View):
    """Activate / deactivate a staff account (never your own)."""

    allowed_roles = (roles.ADMIN,)

    def post(self, request, pk):
        user = get_object_or_404(User.objects.exclude(role=roles.PATIENT), pk=pk)
        if user == request.user:
            messages.error(request, _("You cannot deactivate your own account."))
        else:
            user.is_active = not user.is_active
            user.save(update_fields=["is_active"])
            message = _("%(user)s has been %(state)s.") % {
                "user": user,
                "state": _("activated") if user.is_active else _("deactivated"),
            }
            messages.success(request, message)
        return redirect("accounts:staff_list")
