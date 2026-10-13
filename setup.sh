#!/usr/bin/env bash
# One-shot local setup. Assumes PostgreSQL is running and the database/user from the README exist.
set -euo pipefail

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

[ -f .env ] || cp .env.example .env
python manage.py makemigrations accounts services patients appointments billing
python manage.py migrate
python manage.py seed_demo_data
echo "Done. Start the server with:  source venv/bin/activate && python manage.py runserver"
