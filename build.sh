#!/usr/bin/env bash
# exit on error
set -o errexit

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Running database migrations..."
python -m flask db upgrade

echo "==> Checking if database needs initialization..."
python -c "
from app import create_app, db
from app.models import Season
app = create_app()
with app.app_context():
    if Season.query.count() == 0:
        print('Database is empty, running initialization...')
        exec(open('import_production_data.py').read())
    else:
        print('Database already has data, skipping initialization')
"

echo "==> Build completed successfully!" 