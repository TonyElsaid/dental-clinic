# Dental Clinic Management System

Django 4.2 + PostgreSQL + Django REST Framework + Bootstrap 5.

| Area | What you get |
|------|--------------|
| **Auth & roles** | Custom `User` with roles: Admin (clinic manager), Dentist, Receptionist, Patient. Session login/logout. |
| **Patients** | Register, search (name/phone/email), filter (gender, has allergies), detail page with appointment history, edit, delete (admin only), optional patient-portal login. |
| **Appointments** | Book / edit / cancel, day-week-month agenda, status tracking (scheduled, completed, cancelled, no-show), **double-booking prevention** (dentist *and* patient overlap, enforced under a row lock). |
| **Services** | Catalog with price and estimated duration; duration drives each appointment's end time. |
| **Billing** | Invoice per completed appointment, payments (cash/card/transfer/insurance), status derived automatically (pending / partial / paid), PDF download. |
| **Dashboard** | Today's appointments, upcoming count, appointments this month, total patients, recent patients, outstanding balance (front desk). |
| **REST API** | `/api/patients/`, `/api/services/`, `/api/appointments/`, `/api/invoices/` with the same role rules. |

## Who can do what

| | Admin | Receptionist | Dentist | Patient |
|---|:-:|:-:|:-:|:-:|
| Patients: view | all | all | only own patients | - |
| Patients: create/edit | yes | yes | - | - |
| Patients: delete | yes | - | - | - |
| Appointments: view | all | all | **only their own** | own (portal) |
| Appointments: book/edit | yes | yes | - | - |
| Appointments: cancel | yes | yes | - | - |
| Appointments: mark completed / no-show | yes | yes | own | - |
| Services: view / edit | view+edit | view | view | - |
| Billing & invoices | yes | yes | - | own invoices (PDF) |
| Staff management, Django admin | yes | - | - | - |

## Prerequisites

* Python 3.11+
* PostgreSQL 13+ (server + client libraries are *not* needed to build; `psycopg2-binary` is used)
* Git

## Installation

```bash
git clone <this-repo> dental_clinic && cd dental_clinic
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                # then edit SECRET_KEY and DB_* values
```

Generate a real secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

## Database setup

```bash
sudo -u postgres psql
```
```sql
CREATE DATABASE dental_clinic;
CREATE USER dental_user WITH PASSWORD 'dental_pass';
ALTER DATABASE dental_clinic OWNER TO dental_user;
ALTER USER dental_user CREATEDB;   -- lets `manage.py test` create its test database
\q
```

Use the same values in `.env` (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`).

Create and apply the schema:

```bash
python manage.py makemigrations accounts services patients appointments billing
python manage.py migrate
```

> Migration files are generated on your machine (and should then be committed):
> the custom user model (`accounts.User`) must have its initial migration created
> **before** the first `migrate`, which is why the `makemigrations` step is explicit.

Seed demo data (admin + staff accounts, service catalog, one sample patient):

```bash
python manage.py seed_demo_data
```

Everything above is automated by `./setup.sh`.

## Run

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000/ and log in.

## Default credentials (created by `seed_demo_data`)

| Role | Username | Password |
|------|----------|----------|
| Admin (clinic manager) | `admin` | `Admin@12345` |
| Dentist | `dr_smith`, `dr_jones` | `Clinic@12345` |
| Receptionist | `reception` | `Clinic@12345` |
| Patient (portal) | `patient_jane` | `Clinic@12345` |

**Change all of these immediately in any real deployment.**
Alternatively create your own manager with `python manage.py createsuperuser`
(superusers automatically get the Admin role). Initial data can also be entered
through the Django admin at `/admin/`.

## Typical workflow

1. Receptionist registers a patient (*Patients -> Register patient*).
2. *Book appointment* - pick dentist, service and start time. The end time is
   calculated from the service duration; overlapping bookings are rejected.
3. After the visit the dentist (or front desk) marks it **Completed**.
4. Front desk opens the appointment -> **Generate invoice** -> **Record payment**
   (partial payments supported) -> **Download PDF**.
5. Optionally give the patient portal access (*patient page -> Create portal account*).

## REST API

Session auth (log in via `/api/auth/login/`) or HTTP Basic auth.

```bash
curl -u reception:Clinic@12345 "http://127.0.0.1:8000/api/patients/?search=jane"
curl -u reception:Clinic@12345 -H "Content-Type: application/json" \
     -d '{"patient":1,"dentist":2,"service":1,"date":"2030-01-15","start_time":"09:00"}' \
     http://127.0.0.1:8000/api/appointments/
curl -u dr_smith:Clinic@12345 -X POST -H "Content-Type: application/json" \
     -d '{"status":"completed"}' http://127.0.0.1:8000/api/appointments/1/set_status/
curl -u reception:Clinic@12345 -H "Content-Type: application/json" \
     -d '{"amount":"60.00","method":"cash"}' http://127.0.0.1:8000/api/invoices/1/payments/
```

Browsable API: http://127.0.0.1:8000/api/

## Tests

```bash
python manage.py test
```

## Translations

The interface is available in English and Arabic. Use the language selector in
the navigation bar to switch languages; Arabic pages use a right-to-left layout.
Translation strings are maintained in `locale/ar/LC_MESSAGES/django.po`.

After editing translations, regenerate and compile the Arabic catalog with GNU
gettext installed:

```bash
python manage.py makemessages -l ar
python manage.py compilemessages
```

## Project layout

```
config/        settings (python-decouple), root urls, wsgi/asgi
accounts/      custom User, roles, auth + staff views, shared mixins, seed command
patients/      Patient model, search/filter, CRUD, portal-account creation
services/      Service catalog
appointments/  Appointment model (overlap logic), agenda views, status changes
billing/       Invoice + Payment models, PDF (ReportLab)
dashboard/     role-aware landing page
portal/        patient self-service page
api/           DRF serializers, viewsets, role permissions
templates/     Bootstrap 5 templates
```

## Production notes

* Set `DEBUG=False`, a strong `SECRET_KEY`, real `ALLOWED_HOSTS`; enable
  `SECURE_COOKIES=True` / `SECURE_SSL_REDIRECT=True` behind HTTPS.
* Run `python manage.py collectstatic` and serve `/static/` (e.g. WhiteNoise or nginx)
  and run under gunicorn/uvicorn.
* Bootstrap is loaded from a CDN; vendor it locally for offline clinics.
