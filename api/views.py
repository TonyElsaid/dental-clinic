from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import ProtectedError
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts import roles
from appointments.models import Appointment
from billing.models import Invoice
from patients.models import Patient
from services.models import Service

from .permissions import IsClinicStaff, RolePermission
from .serializers import (
    AppointmentSerializer,
    InvoiceSerializer,
    PatientSerializer,
    PaymentSerializer,
    ServiceSerializer,
    to_drf_error,
)


class ProtectedDeleteMixin:
    """Return 409 instead of a 500 when a protected row is deleted."""

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "This record is referenced by other records and cannot be deleted."},
                status=status.HTTP_409_CONFLICT,
            )


class PatientViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    """Search with ?search=<text>; filter with ?gender=F."""

    serializer_class = PatientSerializer
    permission_classes = [RolePermission]
    read_roles = roles.STAFF + (roles.PATIENT,)
    write_roles = roles.FRONT_DESK
    delete_roles = (roles.ADMIN,)

    def get_queryset(self):
        queryset = Patient.objects.visible_to(self.request.user).search(
            self.request.query_params.get("search")
        )
        gender = self.request.query_params.get("gender")
        return queryset.filter(gender=gender) if gender else queryset


class ServiceViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [RolePermission]
    read_roles = roles.STAFF
    write_roles = (roles.ADMIN,)
    delete_roles = (roles.ADMIN,)


class AppointmentViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    """Filter with ?date=YYYY-MM-DD, ?status=..., ?dentist=<id>."""

    serializer_class = AppointmentSerializer
    permission_classes = [RolePermission]
    read_roles = roles.STAFF + (roles.PATIENT,)
    write_roles = roles.FRONT_DESK
    delete_roles = (roles.ADMIN,)

    def get_queryset(self):
        queryset = Appointment.objects.visible_to(self.request.user).select_related(
            "patient", "dentist", "service"
        )
        params = self.request.query_params
        if params.get("date"):
            queryset = queryset.filter(date=params["date"])
        if params.get("status") in Appointment.Status.values:
            queryset = queryset.filter(status=params["status"])
        if params.get("dentist", "").isdigit():
            queryset = queryset.filter(dentist_id=params["dentist"])
        return queryset

    def perform_create(self, serializer):
        try:
            serializer.save(created_by=self.request.user)
        except DjangoValidationError as exc:  # lost a booking race
            raise to_drf_error(exc)

    def perform_update(self, serializer):
        try:
            serializer.save()
        except DjangoValidationError as exc:
            raise to_drf_error(exc)

    @action(detail=True, methods=["post"], permission_classes=[IsClinicStaff])
    def set_status(self, request, pk=None):
        """POST {"status": "completed"}. Dentists may only touch their own appointments."""
        appointment = self.get_object()
        new_status = request.data.get("status")
        if request.user.is_front_desk:
            permitted = Appointment.Status.values
        else:
            permitted = ["scheduled", "completed", "no_show"]
        if new_status not in permitted:
            return Response({"status": "Invalid or forbidden status."}, status=status.HTTP_400_BAD_REQUEST)
        appointment.status = new_status
        try:
            appointment.save(update_fields=["status", "updated_at"])
        except DjangoValidationError as exc:
            raise to_drf_error(exc)
        return Response(self.get_serializer(appointment).data)


class InvoiceViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Create an invoice for a completed appointment; POST /payments/ to record money."""

    serializer_class = InvoiceSerializer
    permission_classes = [RolePermission]
    read_roles = roles.FRONT_DESK + (roles.PATIENT,)
    write_roles = roles.FRONT_DESK
    delete_roles = ()

    def get_queryset(self):
        queryset = Invoice.objects.select_related("appointment__patient").prefetch_related("payments")
        if self.request.user.is_patient_user:
            queryset = queryset.filter(appointment__patient__user=self.request.user)
        return queryset

    def perform_create(self, serializer):
        appointment = serializer.validated_data["appointment"]
        serializer.save(amount=appointment.service.price)

    @action(detail=True, methods=["post"])
    def payments(self, request, pk=None):
        invoice = self.get_object()
        serializer = PaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data["amount"] > invoice.balance:
            return Response(
                {"amount": f"Exceeds the outstanding balance of {invoice.balance}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save(invoice=invoice)
        invoice.refresh_from_db()
        return Response(self.get_serializer(invoice).data, status=status.HTTP_201_CREATED)
