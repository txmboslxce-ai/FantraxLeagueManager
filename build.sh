#!/usr/bin/env bash
# exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Run database migrations
python -m flask db upgrade

# Import production data (teams, seasons, divisions, sample MOTM data)
python import_production_data.py 