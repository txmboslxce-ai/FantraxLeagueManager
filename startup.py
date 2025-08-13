from app import create_app, db
from app.models import Season
import os

def init_db_if_empty():
    app = create_app()
    with app.app_context():
        # Check if database is empty (no seasons)
        if not Season.query.first():
            print("Database is empty, initializing with data...")
            try:
                # Initialize database schema
                db.create_all()
                
                # Execute SQL file with initial data
                with open('export.sql', 'r') as f:
                    sql_statements = f.read().split(';')
                    for statement in sql_statements:
                        if statement.strip():
                            db.session.execute(statement)
                db.session.commit()
                print("Database initialized successfully!")
            except Exception as e:
                print(f"Error initializing database: {e}")
                db.session.rollback()
        else:
            print("Database already contains data, skipping initialization.")
