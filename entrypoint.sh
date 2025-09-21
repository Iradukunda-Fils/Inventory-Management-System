#!/bin/bash
set -e  # Exit immediately if a command exits with non-zero status
set -u  # Treat unset variables as an error

# --------------------------------
# Wait for PostgreSQL to be ready
# --------------------------------
echo "Waiting for PostgreSQL to start..."
until nc -z db 5432; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 2
done
echo "PostgreSQL is up!"

# --------------------------------
# Make migrations
# --------------------------------
echo "Making migrations..."
python manage.py makemigrations --noinput

# --------------------------------
# Run migrations
# --------------------------------
echo "Running migrations..."
python manage.py migrate --noinput

# --------------------------------
# Create superuser if not exists
# --------------------------------
echo "Checking/creating superuser..."
python manage.py shell << END
from django.contrib.auth import get_user_model
import os

User = get_user_model()
username = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
email = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "admin123")
phone_number = os.getenv("DJANGO_SUPERUSER_PHONE_NUMBER", None)
role = "admin"

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(
        username=username,
        email=email,
        role=role,
        password=password,
        phone_number=phone_number
    )
    print("Superuser created with phone number:", phone_number)
else:
    print("Superuser already exists.")
END

# --------------------------------
# Start the main process
# --------------------------------
echo "Starting container process..."
exec "$@"
