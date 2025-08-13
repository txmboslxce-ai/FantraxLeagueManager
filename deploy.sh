#!/bin/bash
# Deployment script for production environment

echo "Starting deployment process..."

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run database migrations
echo "Running database migrations..."
flask db upgrade

# Check if database exists or needs restoration
if [ ! -f "fantasy_league.db" ]; then
    echo "Database not found. Looking for backup to restore..."
    
    # Find the most recent backup file
    BACKUP_FILE=$(ls -t db_backup_*.sql 2>/dev/null | head -n1)
    
    if [ -n "$BACKUP_FILE" ]; then
        echo "Restoring database from $BACKUP_FILE..."
        python restore_db.py "$BACKUP_FILE"
    else
        echo "No backup found. Initializing fresh database..."
        python init_production_db.py
    fi
else
    echo "Database exists, checking if initialization is needed..."
    python init_production_db.py
fi

# Check if we need to create an admin user
echo "Setting up admin user..."
python -c "
from app import create_app, db
from app.models import User
app = create_app()
with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', email='admin@example.com', is_admin=True)
        admin.set_password('changeme123')
        db.session.add(admin)
        db.session.commit()
        print('Created admin user with password: changeme123')
        print('IMPORTANT: Change this password immediately!')
    else:
        print('Admin user already exists')
"

echo "Deployment complete!"
echo "Don't forget to:"
echo "1. Change the admin password"
echo "2. Set environment variables for production"
echo "3. Configure your web server"
