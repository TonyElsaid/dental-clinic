from django.urls import path

from . import views

app_name = "portal"

urlpatterns = [path("", views.PortalHomeView.as_view(), name="home")]
