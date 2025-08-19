#!/usr/bin/env python3
"""
Direct database import script that will forcefully import all data
"""
import os
from sqlalchemy import create_engine, text
from app import create_app, db

def import_data():
    app = create_app()
    with app.app_context():
        # Source SQLite database
        sqlite_path = os.path.join(os.path.dirname(__file__), 'fantasy_league.db')
        source_engine = create_engine(f'sqlite:///{sqlite_path}')
        
        # Target PostgreSQL database
        target_engine = db.engine
        
        print("Starting direct data import...")
        
        try:
            with source_engine.connect() as source_conn, target_engine.connect() as target_conn:
                # Disable foreign key checks
                target_conn.execute(text('SET session_replication_role = replica;'))
                
                # Clear existing data
                tables = [
                    'title', 'cup_group_match', 'cup_group', 'cup_round',
                    'cup_competition', 'fixture', 'manager_of_the_month',
                    'team_season', 'gameweek', 'division', 'team', 'season'
                ]
                
                print("Clearing existing data...")
                for table in tables:
                    target_conn.execute(text(f'TRUNCATE TABLE {table} CASCADE;'))
                
                print("Importing data...")
                # Import in reverse order (for dependencies)
                for table in reversed(tables):
                    print(f"Processing {table}...")
                    # Get data from SQLite
                    result = source_conn.execute(text(f'SELECT * FROM {table}'))
                    rows = result.fetchall()
                    
                    if rows:
                        # Get column names
                        columns = result.keys()
                        column_list = ', '.join(columns)
                        placeholders = ', '.join([':' + col for col in columns])
                        
                        # Create INSERT statement
                        insert_stmt = f'INSERT INTO {table} ({column_list}) VALUES ({placeholders})'
                        
                        # Insert each row
                        for row in rows:
                            row_dict = dict(zip(columns, row))
                            target_conn.execute(text(insert_stmt), row_dict)
                            target_conn.execute(text('COMMIT;'))
                        
                        print(f"- Imported {len(rows)} rows into {table}")
                
                # Re-enable foreign key checks
                target_conn.execute(text('SET session_replication_role = default;'))
                print("Data import completed successfully!")
                
                # Verify the import
                for table in tables:
                    result = target_conn.execute(text(f'SELECT COUNT(*) FROM {table}'))
                    count = result.scalar()
                    print(f"Table {table}: {count} rows")
                
        except Exception as e:
            print(f"Error during import: {str(e)}")
            raise

if __name__ == '__main__':
    import_data()
