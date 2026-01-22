#!/bin/sh

# Wait for DB to be ready (optional but recommended)
# while ! nc -z $SQL_HOST $SQL_PORT; do
#   echo "Waiting for SQL..."
#   sleep 1
# done

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Applying migrations..."
python manage.py migrate

# Start Gunicorn
# bind: 0.0.0.0:8000 exposes it to the Docker network
echo "Starting Gunicorn..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3