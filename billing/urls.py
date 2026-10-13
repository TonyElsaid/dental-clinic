from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    path("", views.InvoiceListView.as_view(), name="list"),
    path("create/<int:appointment_pk>/", views.InvoiceCreateView.as_view(), name="create"),
    path("<int:pk>/", views.InvoiceDetailView.as_view(), name="detail"),
    path("<int:pk>/payment/", views.PaymentCreateView.as_view(), name="payment"),
    path("<int:pk>/pdf/", views.InvoicePDFView.as_view(), name="pdf"),
]
