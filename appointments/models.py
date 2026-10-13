from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models, transaction
from django.urls import reverse


class AppointmentQuerySet(models.QuerySet):
    def visible_to(self, user):
        """Dentists see only their own appointments; patients only theirs."""
        if user.is_front_desk:
            return self
        if user.is_dentist:
            return self.filter(dentist=user)
        if user.is_patient_user:
            return self.filter(patient__user=user)
        return self.none()


class Appointment(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No-show"

    # Only these statuses occupy the dentist's / patient's time slot.
    BLOCKING_STATUSES = (Status.SCHEDULED, Status.COMPLETED)

    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT, related_name="appointments"
    )
    dentist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="dentist_appointments",
        limit_choices_to={"role": "dentist"},
    )
    service = models.ForeignKey(
        "services.Service", on_delete=models.PROTECT, related_name="appointments"
    )
    date = models.DateField()
    start_time = models.TimeField()
    # Derived from start_time + service duration; never entered by hand.
    end_time = models.TimeField(editable=False, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AppointmentQuerySet.as_manager()

    class Meta:
        ordering = ["date", "start_time"]
        indexes = [models.Index(fields=["date", "dentist"])]

    def __str__(self):
        return f"{self.patient} - {self.service} on {self.date} {self.start_time:%H:%M}"

    def get_absolute_url(self):
        return reverse("appointments:detail", args=[self.pk])

    @property
    def invoice_or_none(self):
        try:
            return self.invoice
        except ObjectDoesNotExist:
            return None

    # ------------------------------------------------------------------ logic
    def compute_end_time(self):
        """start_time + the service's estimated duration (must end the same day)."""
        start = datetime.combine(self.date, self.start_time)
        end = start + timedelta(minutes=self.service.duration_minutes)
        if end.date() != self.date:
            raise ValidationError({"start_time": "The appointment must finish before midnight."})
        return end.time()

    def check_conflicts(self):
        """Raise ValidationError if the dentist or patient is already booked.

        Two appointments overlap when each starts before the other ends.
        Cancelled and no-show appointments free the slot.
        """
        if self.status not in self.BLOCKING_STATUSES or not self.end_time:
            return
        overlapping = (
            Appointment.objects.filter(
                date=self.date,
                status__in=self.BLOCKING_STATUSES,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time,
            )
            .exclude(pk=self.pk)
        )
        if self.dentist_id and overlapping.filter(dentist_id=self.dentist_id).exists():
            raise ValidationError(
                {"start_time": "This dentist is already booked during that time slot."}
            )
        if self.patient_id and overlapping.filter(patient_id=self.patient_id).exists():
            raise ValidationError(
                {"start_time": "This patient already has an appointment during that time slot."}
            )

    def clean(self):
        super().clean()
        if self.dentist_id and self.dentist.role != "dentist":
            raise ValidationError({"dentist": "The selected user is not a dentist."})
        if not (self.service_id and self.date and self.start_time):
            return  # field-level errors are reported elsewhere
        self.end_time = self.compute_end_time()
        self.check_conflicts()

    def save(self, *args, **kwargs):
        if self.service_id and self.date and self.start_time:
            self.end_time = self.compute_end_time()
        with transaction.atomic():
            if self.dentist_id and self.status in self.BLOCKING_STATUSES:
                # Lock the dentist's row so two simultaneous bookings for the same
                # dentist are serialised; the loser sees the conflict below.
                get_user_model().objects.select_for_update().filter(pk=self.dentist_id).first()
            self.check_conflicts()
            super().save(*args, **kwargs)
