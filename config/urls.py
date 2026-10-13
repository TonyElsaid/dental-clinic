from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("accounts/", include("accounts.urls")),
    path("services/", include("services.urls")),
    path("patients/", include("patients.urls")),
    path("appointments/", include("appointments.urls")),
    path("billing/", include("billing.urls")),
    path("portal/", include("portal.urls")),
    path("api/", include("api.urls")),
    path("", include("dashboard.urls")),
]
