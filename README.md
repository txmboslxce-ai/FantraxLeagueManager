# Fantasy League Application

## Local Development

1. Clone the repository
2. Create a virtual environment: `python -m venv .venv`
3. Activate it: `source .venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Run: `python run.py`

## Production Deployment

### Option 1: Automated Deployment Script

Run the deployment script:
```bash
./deploy.sh
```

### Option 2: Manual Deployment

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export FLASK_ENV=production
   export SECRET_KEY=your-secret-key-here
   export DATABASE_URL=your-database-url  # Optional, defaults to SQLite
   ```

3. **Initialize the database:**
   ```bash
   flask db upgrade
   python init_production_db.py
   ```

4. **Create admin user (if needed):**
   ```bash
   python -c "
   from app import create_app, db
   from app.models import User
   app = create_app()
   with app.app_context():
       admin = User(username='admin', email='admin@example.com', is_admin=True)
       admin.set_password('your-secure-password')
       db.session.add(admin)
       db.session.commit()
   "
   ```

5. **Run the application:**
   ```bash
   python run.py
   ```

## Database Migrations

When you make model changes:

1. Create migration: `flask db migrate -m "description of changes"`
2. Apply migration: `flask db upgrade`
3. Commit the migration file to git

## Important Notes

- **Never commit database files** (they're in `.gitignore`)
- **Always use migrations** for schema changes
- **Run `init_production_db.py`** on fresh deployments
- **Change default admin password** immediately after deployment
- **Use environment variables** for sensitive configuration in production

## Troubleshooting

If you get relationship errors after deployment:
1. Make sure all migrations are applied: `flask db upgrade`
2. Run the initialization script: `python init_production_db.py`
3. Restart the application

## Shipping the Existing SQLite Database

This repository is currently configured to commit the `fantasy_league.db` file so that a snapshot of the current league state can be deployed directly (the `.gitignore` rule for `*.db` is overridden for this specific filename). Be aware:

- SQLite is single-file and not ideal for concurrent production usage; prefer PostgreSQL in real production.
- If you later migrate to PostgreSQL, set `DATABASE_URL` and run `flask db upgrade` plus appropriate data import.

## Automatic Admin Creation

On application startup, if no admin user exists, the app creates one:

- Username: `admin`
- Email: `admin@example.com`
- Password: value of `DEFAULT_ADMIN_PASSWORD` env var, else `admin`

Change this password immediately after first login in production.

## File Structure

- `migrations/` - Database migration files (commit these)
- `app/models.py` - Database models with relationships
- `init_production_db.py` - Production database initialization
- `deploy.sh` - Automated deployment script
