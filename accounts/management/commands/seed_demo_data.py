"""Create demo users, services and a sample patient. Safe to run repeatedly."""
from django.core.management.base import BaseCommand

from accounts.models import User
from patients.models import Patient
from services.models import Service

DEMO_PASSWORD = "Clinic@12345"

SERVICES = [
    ("Dental Cleaning", "Scaling and polishing", "60.00", 30),
    ("Check-up & Consultation", "Examination and treatment plan", "40.00", 20),
    ("Filling", "Composite tooth filling", "120.00", 45),
    ("Tooth Extraction", "Simple extraction", "150.00", 45),
    ("Root Canal Treatment", "Endodontic treatment", "450.00", 90),
    ("Teeth Whitening", "In-office whitening", "250.00", 60),
    ("Dental X-Ray", "Digital radiograph", "35.00", 15),
]


class Command(BaseCommand):
    help = "Seed demo accounts, the services catalog and one demo patient."

    def handle(self, *args, **options):
        accounts = [
            ("admin", "Clinic", "Manager", User.Role.ADMIN),
            ("dr_smith", "Sarah", "Smith", User.Role.DENTIST),
            ("dr_jones", "Mark", "Jones", User.Role.DENTIST),
            ("reception", "Rita", "Front", User.Role.RECEPTIONIST),
        ]
        for username, first, last, role in accounts:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"first_name": first, "last_name": last, "role": role,
                          "email": f"{username}@example.com"},
            )
            if created:
                user.set_password("Admin@12345" if username == "admin" else DEMO_PASSWORD)
                user.save()
            self.stdout.write(f"{'created' if created else 'exists '} user {username}")

        for name, description, price, minutes in SERVICES:
            Service.objects.get_or_create(
                name=name,
                defaults={"description": description, "price": price, "duration_minutes": minutes},
            )

        patient, created = Patient.objects.get_or_create(
            first_name="Jane", last_name="Doe",
            defaults={"date_of_birth": "1990-05-17", "gender": "F", "phone": "+1 555 0123",
                      "email": "jane@example.com", "allergies": "Penicillin"},
        )
        if created and not patient.user_id:
            portal_user = User.objects.create_user(
                username="patient_jane", password=DEMO_PASSWORD, first_name="Jane",
                last_name="Doe", email="jane@example.com", role=User.Role.PATIENT,
            )
            patient.user = portal_user
            patient.save(update_fields=["user"])

        self.stdout.write(self.style.SUCCESS("Demo data ready. Change these passwords before going live!"))
