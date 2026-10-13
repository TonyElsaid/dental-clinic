"""Reusable view/form mixins shared by all apps."""
from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import ProtectedError
from django.shortcuts import redirect


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restrict a view to users whose role is in ``allowed_roles``."""

    allowed_roles = ()

    def test_func(self):
        return self.request.user.role in self.allowed_roles

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "You do not have permission to access that page.")
            return redirect("dashboard:home")
        return super().handle_no_permission()


class BootstrapFormMixin:
    """Add Bootstrap 5 CSS classes to every widget of a form."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                css = "form-select"
            else:
                css = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()


class PageContextMixin:
    """Provide title / submit label / cancel link to the shared form templates."""

    page_title = ""
    submit_label = "Save"
    cancel_url = None

    def get_cancel_url(self):
        return self.cancel_url

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title,
            submit_label=self.submit_label,
            cancel_url=self.get_cancel_url(),
        )
        return context


class SafeDeleteMixin:
    """Show a friendly message instead of a 500 when a protected row is deleted."""

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                "This record is referenced by other records (e.g. appointments or "
                "invoices) and cannot be deleted.",
            )
            return redirect(self.get_cancel_url())


class QueryStringMixin:
    """Expose the current query string (minus ``page``) for pagination links."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop("page", None)
        context["query_string"] = params.urlencode()
        return context
