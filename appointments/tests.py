from datetime import date, time, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from patients.models import Patient
from services.models import Service

from .models import Appointment


class AppointmentTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dentist = User.objects.create_user("dr1", password="pw12345!x", role="dentist")
        cls.dentist2 = User.objects.create_user("dr2", password="pw12345!x", role="dentist")
        cls.receptionist = User.objects.create_user("rec", password="pw12345!x", role="receptionist")
        cls.patient = Patient.objects.create(
            first_name="Ann", last_name="Lee", date_of_birth=date(1990, 1, 1), phone="+1 555 0001"
        )
        cls.patient2 = Patient.objects.create(
            first_name="Bob", last_name="Ray", date_of_birth=date(1985, 2, 2), phone="+1 555 0002"
        )
        cls.service = Service.objects.create(name="Filling", price="100.00", duration_minutes=60)
        cls.day = timezone.localdate() + timedelta(days=1)

    def make(self, start, dentist=None, patient=None, status=Appointment.Status.SCHEDULED):
        return Appointment(
            patient=patient or self.patient, dentist=dentist or self.dentist,
            service=self.service, date=self.day, start_time=start, status=status,
        )


class DoubleBookingTests(AppointmentTestBase):
    def test_end_time_is_start_plus_duration(self):
        appointment = self.make(time(9, 0))
        appointment.save()
        self.assertEqual(appointment.end_time, time(10, 0))

    def test_overlap_same_dentist_rejected(self):
        self.make(time(9, 0)).save()
        with self.assertRaises(ValidationError):
            self.make(time(9, 30), patient=self.patient2).save()

    def test_back_to_back_allowed(self):
        self.make(time(9, 0)).save()
        self.make(time(10, 0), patient=self.patient2).save()  # no error

    def test_other_dentist_allowed(self):
        self.make(time(9, 0)).save()
        self.make(time(9, 0), dentist=self.dentist2, patient=self.patient2).save()

    def test_same_patient_cannot_be_in_two_places(self):
        self.make(time(9, 0)).save()
        with self.assertRaises(ValidationError):
            self.make(time(9, 15), dentist=self.dentist2).save()

    def test_cancelled_appointment_frees_slot(self):
        self.make(time(9, 0), status=Appointment.Status.CANCELLED).save()
        self.make(time(9, 0)).save()

    def test_cannot_cross_midnight(self):
        with self.assertRaises(ValidationError):
            self.make(time(23, 30)).save()


class AppointmentViewTests(AppointmentTestBase):
    def payload(self, start="09:00"):
        return {
            "patient": self.patient.pk, "dentist": self.dentist.pk, "service": self.service.pk,
            "date": self.day.isoformat(), "start_time": start, "status": "scheduled", "notes": "",
        }

    def test_receptionist_can_book(self):
        self.client.force_login(self.receptionist)
        response = self.client.post(reverse("appointments:create"), self.payload())
        self.assertEqual(Appointment.objects.count(), 1)
        self.assertEqual(response.status_code, 302)

    def test_form_rejects_double_booking(self):
        self.client.force_login(self.receptionist)
        self.client.post(reverse("appointments:create"), self.payload())
        data = self.payload("09:30")
        data["patient"] = self.patient2.pk
        response = self.client.post(reverse("appointments:create"), data)
        self.assertEqual(response.status_code, 200)  # form re-rendered with errors
        self.assertEqual(Appointment.objects.count(), 1)

    def test_dentist_cannot_book(self):
        self.client.force_login(self.dentist)
        self.client.post(reverse("appointments:create"), self.payload())
        self.assertEqual(Appointment.objects.count(), 0)

    def test_dentist_sees_only_own_appointments(self):
        mine = self.make(time(9, 0)); mine.save()
        theirs = self.make(time(9, 0), dentist=self.dentist2, patient=self.patient2); theirs.save()
        self.client.force_login(self.dentist)
        response = self.client.get(reverse("appointments:list"), {"date": self.day.isoformat()})
        self.assertEqual(list(response.context["appointments"]), [mine])
        self.assertEqual(self.client.get(theirs.get_absolute_url()).status_code, 404)

    def test_dentist_can_mark_own_appointment_completed(self):
        appointment = self.make(time(9, 0)); appointment.save()
        self.client.force_login(self.dentist)
        self.client.post(reverse("appointments:status", args=[appointment.pk]), {"status": "completed"})
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, "completed")

    def test_dentist_cannot_cancel(self):
        appointment = self.make(time(9, 0)); appointment.save()
        self.client.force_login(self.dentist)
        self.client.post(reverse("appointments:status", args=[appointment.pk]), {"status": "cancelled"})
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, "scheduled")
