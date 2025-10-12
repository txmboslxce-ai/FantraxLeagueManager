from app import db, create_app
from app import create_app, db
from sqlalchemy import text
import os

def fix_fixture_sequence():
    app = create_app()
    with app.app_context():
        # Check if we're using PostgreSQL (production) or SQLite (development)
        if 'postgresql' in str(db.engine.url):
            # PostgreSQL sequence setup
            db.session.execute(text("""
                DO $$
                BEGIN
                    -- Create sequence if it doesn't exist
                    CREATE SEQUENCE IF NOT EXISTS fixture_id_seq;
                    
                    -- Set the sequence to be owned by the fixture.id column
                    ALTER TABLE fixture ALTER COLUMN id SET DEFAULT nextval('fixture_id_seq');
                    ALTER SEQUENCE fixture_id_seq OWNED BY fixture.id;
                    
                    -- Set the current value to the max id
                    PERFORM setval('fixture_id_seq', COALESCE((SELECT MAX(id) FROM fixture), 0));
                END $$;
            """))
        else:
            # SQLite doesn't support sequences, but we can at least check if AUTOINCREMENT is set
            result = db.session.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name='fixture'")).fetchone()
            if result and 'AUTOINCREMENT' not in result[0].upper():
                print("Warning: SQLite table 'fixture' may not have AUTOINCREMENT set properly.")
                print("This is fine for development, but make sure to run this script in production with PostgreSQL.")
        
        db.session.commit()
        print("Database check completed successfully!")

if __name__ == '__main__':
    fix_fixture_sequence()