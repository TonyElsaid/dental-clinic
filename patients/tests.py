from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Patient


class PatientTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.receptionist = User.objects.create_user("rec", password="pw12345!x", role="receptionist")
        cls.admin = User.objects.create_user("adm", password="pw12345!x", role="admin")
        Patient.objects.create(first_name="Ann", last_name="Lee", date_of_birth=date(1990, 1, 1), phone="+1 555 0001")
        Patient.objects.create(first_name="Bob", last_name="Ray", date_of_birth=date(1985, 2, 2), phone="+1 555 0002",
                               allergies="Latex")

    def test_search_by_name_and_allergy_filter(self):
        self.client.force_login(self.receptionist)
        response = self.client.get(reverse("patients:list"), {"q": "ann lee"})
        self.assertEqual([p.first_name for p in response.context["patients"]], ["Ann"])
        response = self.client.get(reverse("patients:list"), {"allergies": "yes"})
        self.assertEqual([p.first_name for p in response.context["patients"]], ["Bob"])

    def test_register_patient(self):
        self.client.force_login(self.receptionist)
        response = self.client.post(reverse("patients:create"), {
            "first_name": "Cy", "last_name": "Poe", "date_of_birth": "2000-03-04",
            "gender": "M", "phone": "+1 555 0003", "email": "", "address": "",
            "emergency_contact_name": "", "emergency_contact_phone": "",
            "medical_history": "", "allergies": "",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Patient.objects.filter(last_name="Poe").exists())

    def test_future_dob_rejected(self):
        self.client.force_login(self.receptionist)
        self.client.post(reverse("patients:create"), {
            "first_name": "Z", "last_name": "Z", "date_of_birth": "2999-01-01", "gender": "M", "phone": "+1 555 0009",
        })
        self.assertFalse(Patient.objects.filter(first_name="Z").exists())

    def test_only_admin_can_delete(self):
        patient = Patient.objects.first()
        self.client.force_login(self.receptionist)
        self.client.post(reverse("patients:delete", args=[patient.pk]))
        self.assertTrue(Patient.objects.filter(pk=patient.pk).exists())
        self.client.force_login(self.admin)
        self.client.post(reverse("patients:delete", args=[patient.pk]))
        self.assertFalse(Patient.objects.filter(pk=patient.pk).exists())
