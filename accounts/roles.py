"""Role identifiers and common role groups used for authorization."""
ADMIN = "admin"
DENTIST = "dentist"
RECEPTIONIST = "receptionist"
PATIENT = "patient"

STAFF = (ADMIN, DENTIST, RECEPTIONIST)
FRONT_DESK = (ADMIN, RECEPTIONIST)  # may manage patients, appointments, billing
