from django.test import TestCase
from django.urls import reverse

from patients.models import Patient

from .models import User


class RoleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.patient_user = User.objects.create_user("pat", password="pw12345!x", role="patient")
        cls.receptionist = User.objects.create_user("rec", password="pw12345!x", role="receptionist")

    def test_superuser_becomes_admin(self):
        user = User.objects.create_superuser("boss", "b@example.com", "pw12345!x")
        self.assertEqual(user.role, User.Role.ADMIN)

    def test_default_role_is_patient(self):
        self.assertEqual(User.objects.create_user("x", password="y").role, User.Role.PATIENT)

    def test_login_required(self):
        response = self.client.get(reverse("patients:list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_patient_redirected_from_dashboard_to_portal(self):
        self.client.force_login(self.patient_user)
        self.assertRedirects(self.client.get(reverse("dashboard:home")), reverse("portal:home"))

    def test_patient_cannot_open_patient_list(self):
        self.client.force_login(self.patient_user)
        response = self.client.get(reverse("patients:list"))
        self.assertRedirects(response, reverse("dashboard:home"), fetch_redirect_response=False)

    def test_receptionist_cannot_manage_staff(self):
        self.client.force_login(self.receptionist)
        response = self.client.get(reverse("accounts:staff_list"))
        self.assertEqual(response.status_code, 302)
