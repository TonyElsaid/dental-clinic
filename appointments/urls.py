from django.urls import path

from . import views

app_name = "appointments"

urlpatterns = [
    path("", views.AppointmentListView.as_view(), name="list"),
    path("new/", views.AppointmentCreateView.as_view(), name="create"),
    path("<int:pk>/", views.AppointmentDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.AppointmentUpdateView.as_view(), name="update"),
    path("<int:pk>/status/", views.AppointmentStatusView.as_view(), name="status"),
    path("<int:pk>/delete/", views.AppointmentDeleteView.as_view(), name="delete"),
]
