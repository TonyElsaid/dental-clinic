from django.core.validators import MinValueValidator
from django.db import models


class Service(models.Model):
    """A dental procedure offered by the clinic."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    duration_minutes = models.PositiveIntegerField(
        default=30,
        validators=[MinValueValidator(5)],
        help_text="Estimated duration in minutes (used to block the dentist's time).",
    )
    is_active = models.BooleanField(default=True, help_text="Inactive services cannot be booked.")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
