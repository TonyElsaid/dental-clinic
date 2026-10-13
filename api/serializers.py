from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers

from appointments.models import Appointment
from billing.models import Invoice, Payment
from patients.models import Patient
from services.models import Service


def to_drf_error(exc):
    """Convert a Django ValidationError into a DRF one."""
    if hasattr(exc, "error_dict"):
        return serializers.ValidationError(exc.message_dict)
    return serializers.ValidationError(exc.messages)


class PatientSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    age = serializers.IntegerField(read_only=True)

    class Meta:
        model = Patient
        fields = [
            "id", "first_name", "last_name", "full_name", "age", "date_of_birth", "gender",
            "phone", "email", "address", "emergency_contact_name", "emergency_contact_phone",
            "medical_history", "allergies", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_date_of_birth(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        return value


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name", "description", "price", "duration_minutes", "is_active"]


class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    dentist_name = serializers.CharField(source="dentist.__str__", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id", "patient", "patient_name", "dentist", "dentist_name", "service", "service_name",
            "date", "start_time", "end_time", "status", "notes", "created_at",
        ]
        read_only_fields = ["end_time", "created_at"]

    def validate(self, attrs):
        """Run the same model rules as the web forms (overlap, dentist role...)."""
        if self.instance:
            candidate = Appointment.objects.get(pk=self.instance.pk)
            for key, value in attrs.items():
                setattr(candidate, key, value)
        else:
            candidate = Appointment(**attrs)
            if candidate.date and candidate.date < timezone.localdate():
                raise serializers.ValidationError({"date": "Cannot book in the past."})
            if candidate.service_id and not candidate.service.is_active:
                raise serializers.ValidationError({"service": "This service is not available."})
        try:
            candidate.clean()
        except DjangoValidationError as exc:
            raise to_drf_error(exc)
        return attrs


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "amount", "method", "reference", "paid_at"]
        read_only_fields = ["paid_at"]


class InvoiceSerializer(serializers.ModelSerializer):
    payments = PaymentSerializer(many=True, read_only=True)
    balance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "invoice_number", "appointment", "issue_date", "amount", "amount_paid",
            "balance", "status", "notes", "payments",
        ]
        read_only_fields = ["invoice_number", "issue_date", "amount", "amount_paid", "status"]

    def validate_appointment(self, appointment):
        if appointment.status != Appointment.Status.COMPLETED:
            raise serializers.ValidationError("Only completed appointments can be invoiced.")
        return appointment
