from django.urls import path

from . import views

app_name = "patients"

urlpatterns = [
    path("", views.PatientListView.as_view(), name="list"),
    path("new/", views.PatientCreateView.as_view(), name="create"),
    path("<int:pk>/", views.PatientDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.PatientUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", views.PatientDeleteView.as_view(), name="delete"),
    path("<int:pk>/portal-account/", views.PortalAccountCreateView.as_view(), name="portal_account"),
]
