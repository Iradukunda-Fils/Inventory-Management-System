#!/bin/bash

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to start..."
while ! nc -z db 5432; do
  sleep 2
done

echo "starting virtual environment..."
. .venv/bin/activate


# Run migrations
echo "Running migrations..."
python manage.py migrate

python manage.py collectstatic --noinput

# Create superuser only if it doesn't exist
echo "Creating superuser..."
python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
username = "${DJANGO_SUPERUSER_USERNAME}"
email = "${DJANGO_SUPERUSER_EMAIL}"
password = "${DJANGO_SUPERUSER_PASSWORD}"
role = "admin"

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(
        username=username,
        email=email,
        role=role,
        password=password
    )
    print("Superuser created.")
else:
    print("Superuser already exists.")
END

# Start Gunicorn or whatever command is passed to the container
exec "$@"
