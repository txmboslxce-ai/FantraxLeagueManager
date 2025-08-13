#!/usr/bin/env bash
# exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Run database migrations
python -m flask db upgrade

# Initialize database with basic data if needed
python init_production_db.py 