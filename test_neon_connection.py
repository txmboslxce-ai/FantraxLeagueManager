from sqlalchemy import create_engine, text
import os

# Get the database URL from environment
db_url = os.environ.get('DATABASE_URL')

if db_url:
    # Replace postgresql:// with postgresql+pg8000:// for the pg8000 driver
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgresql+pg8000://', 1)
    elif db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql+pg8000://', 1)

    # Remove any SSL parameters from the URL
    if '?' in db_url:
        db_url = db_url.split('?')[0]

    # Create engine with SSL configuration
    engine = create_engine(
        db_url,
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800,
        connect_args={
            'ssl': True,
            'ssl_context': True,
        }
    )

    try:
        # Test the connection
        with engine.connect() as conn:
            result = conn.execute(text('SELECT 1')).scalar()
            print(f"Connection successful! Test query result: {result}")
            
            # Try to get table names
            result = conn.execute(text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'"))
            tables = result.fetchall()
            print("\nAvailable tables:")
            for table in tables:
                print(f"- {table[0]}")
                
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
else:
    print("No DATABASE_URL environment variable found")
