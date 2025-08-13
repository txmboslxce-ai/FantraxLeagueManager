#!/usr/bin/env bash
# exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Run database migrations
flask db upgrade

# Start Gunicorn
exec gunicorn wsgi:app --bind 0.0.0.0:$PORT 