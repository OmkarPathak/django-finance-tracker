#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Function to wait for database
wait_for_db() {
    echo "Waiting for database to be ready..."
    while ! python -c "
import os
import sys
import dj_database_url
import psycopg2
db_url = os.environ.get('DATABASE_URL', '')
if db_url:
    config = dj_database_url.parse(db_url)
    try:
        conn = psycopg2.connect(
            host=config['HOST'],
            port=config['PORT'],
            user=config['USER'],
            password=config['PASSWORD'],
            dbname=config['NAME']
        )
        conn.close()
        sys.exit(0)
    except psycopg2.OperationalError:
        sys.exit(1)
else:
    sys.exit(0)
" 2>/dev/null; do
        echo "Database is unavailable - sleeping 2 seconds..."
        sleep 2
    done
    echo "Database is available!"
}

# Wait for database
wait_for_db

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Collect static files (only in production)
if [ "$DEBUG" != "True" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput --clear
fi

# Setup Demo User (optional, can be disabled in production)
if [ "$SETUP_DEMO_USER" = "True" ]; then
    echo "Setting up Demo User..."
    python manage.py setup_demo_user || true
fi

# Execute the passed command (e.g., gunicorn)
echo "Starting application..."
exec "$@"
