#!/bin/sh

# Fail on error
set -e

echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."

# Wait for DB to be up
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
done

echo "PostgreSQL started"

echo "Waiting for Redis at $REDIS_URL..."
# Simple check for Redis (parsing URL slightly hard in sh, expecting host in env var if needed, 
# but for now we skip strict redis check or use python)

echo "App: Running Migrations..."
python manage.py migrate

echo "App: Starting Server..."
# Execute the passed command or default to daphne
if [ "$#" -eq 0 ]; then
    exec daphne -b 0.0.0.0 -p 8000 project_harvey.asgi:application
else
    exec "$@"
fi
