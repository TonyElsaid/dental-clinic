from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "api"

router = DefaultRouter()
router.register("patients", views.PatientViewSet, basename="patient")
router.register("services", views.ServiceViewSet, basename="service")
router.register("appointments", views.AppointmentViewSet, basename="appointment")
router.register("invoices", views.InvoiceViewSet, basename="invoice")

urlpatterns = [
    path("", include(router.urls)),
    path("auth/", include("rest_framework.urls")),
]
