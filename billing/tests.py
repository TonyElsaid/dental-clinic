from datetime import date, time, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from appointments.models import Appointment
from patients.models import Patient
from services.models import Service

from .models import Invoice, Payment


class BillingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.receptionist = User.objects.create_user("rec", password="pw12345!x", role="receptionist")
        cls.dentist = User.objects.create_user("dr", password="pw12345!x", role="dentist")
        cls.pat_user = User.objects.create_user("pat", password="pw12345!x", role="patient")
        cls.other_user = User.objects.create_user("other", password="pw12345!x", role="patient")
        cls.patient = Patient.objects.create(
            first_name="Ann", last_name="Lee", date_of_birth=date(1990, 1, 1),
            phone="+1 555 0001", user=cls.pat_user,
        )
        service = Service.objects.create(name="Filling", price="120.00", duration_minutes=30)
        cls.appointment = Appointment.objects.create(
            patient=cls.patient, dentist=cls.dentist, service=service,
            date=timezone.localdate() + timedelta(days=1), start_time=time(9, 0),
            status=Appointment.Status.COMPLETED,
        )

    def make_invoice(self):
        return Invoice.objects.create(appointment=self.appointment, amount=Decimal("120.00"))

    def test_invoice_number_generated(self):
        self.assertRegex(self.make_invoice().invoice_number, r"^INV-\d{4}-\d{5}$")

    def test_payment_status_transitions(self):
        invoice = self.make_invoice()
        self.assertEqual(invoice.status, "pending")
        Payment.objects.create(invoice=invoice, amount=Decimal("20.00"))
        invoice.refresh_from_db()
        self.assertEqual((invoice.status, invoice.balance), ("partial", Decimal("100.00")))
        Payment.objects.create(invoice=invoice, amount=Decimal("100.00"))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, "paid")

    def test_generate_invoice_view_uses_service_price(self):
        self.client.force_login(self.receptionist)
        self.client.post(reverse("billing:create", args=[self.appointment.pk]))
        self.assertEqual(Invoice.objects.get().amount, Decimal("120.00"))

    def test_overpayment_rejected(self):
        invoice = self.make_invoice()
        self.client.force_login(self.receptionist)
        self.client.post(reverse("billing:payment", args=[invoice.pk]), {"amount": "500", "method": "cash"})
        self.assertEqual(Payment.objects.count(), 0)

    def test_pdf_owner_ok_stranger_forbidden(self):
        invoice = self.make_invoice()
        url = reverse("billing:pdf", args=[invoice.pk])
        self.client.force_login(self.pat_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get(url).status_code, 403)
