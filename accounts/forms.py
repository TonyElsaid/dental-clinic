from django.contrib.auth.forms import UserCreationForm

from .mixins import BootstrapFormMixin
from .models import User


class StaffCreateForm(BootstrapFormMixin, UserCreationForm):
    """Admin form to create clinic staff (patients get accounts from their record)."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = [
            (value, label)
            for value, label in User.Role.choices
            if value != User.Role.PATIENT
        ]
        for name in ("first_name", "last_name", "email"):
            self.fields[name].required = True
