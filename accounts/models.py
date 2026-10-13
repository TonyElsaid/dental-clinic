from django.contrib.auth.models import AbstractUser
from django.db import models

from . import roles


class User(AbstractUser):
    """Custom user with a clinic role."""

    class Role(models.TextChoices):
        ADMIN = roles.ADMIN, "Admin (Clinic Manager)"
        DENTIST = roles.DENTIST, "Dentist"
        RECEPTIONIST = roles.RECEPTIONIST, "Receptionist"
        PATIENT = roles.PATIENT, "Patient"

    # Least privilege by default: an account without an explicit role is a patient.
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PATIENT)
    phone = models.CharField(max_length=20, blank=True)

    def save(self, *args, **kwargs):
        # Keep Django-admin superusers and clinic admins in sync so that
        # `createsuperuser` produces a working clinic manager.
        if self.is_superuser:
            self.role = self.Role.ADMIN
        if self.role == self.Role.ADMIN:
            self.is_staff = True
            self.is_superuser = True
        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def is_clinic_admin(self):
        return self.role == roles.ADMIN

    @property
    def is_dentist(self):
        return self.role == roles.DENTIST

    @property
    def is_receptionist(self):
        return self.role == roles.RECEPTIONIST

    @property
    def is_patient_user(self):
        return self.role == roles.PATIENT

    @property
    def is_front_desk(self):
        return self.role in roles.FRONT_DESK

    @property
    def is_clinic_staff(self):
        return self.role in roles.STAFF
