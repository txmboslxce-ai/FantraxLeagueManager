import os
import sys
from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text

def check_database(use_neon=True):
    # Set up the environment before importing the app
    if use_neon:
        os.environ['RENDER'] = '1'
    else:
        if 'RENDER' in os.environ:
            del os.environ['RENDER']
            
    # Force reload config module to pick up new environment
    import config
    from importlib import reload
    reload(config)
    
    # Create app context
    app = create_app(config.Config)
    
    with app.app_context():
        print(f"\n=== Checking {'NeonDB' if use_neon else 'SQLite'} ===")
        print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        
        try:
            # Test database connection
            with db.engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).fetchone()
                print("✅ Database connection successful")
        except Exception as e:
            print(f"❌ Database connection failed: {str(e)}")
            return
            
        # Check for admin user
        try:
            admin = User.query.filter_by(username='admin').first()
        except Exception as e:
            print(f"❌ Error querying admin user: {str(e)}")
            return
        
        if not admin:
            print("No admin user found!")
            return
        
        print(f"Admin user details:")
        print(f"Username: {admin.username}")
        print(f"Email: {admin.email}")
        print(f"Is admin: {admin.is_admin}")
        print(f"Password hash: {admin.password_hash}")
        
        # Test password verification
        test_password = 'fantrax13'
        print(f"\nTesting password verification:")
        print(f"Test password: {test_password}")
        if check_password_hash(admin.password_hash, test_password):
            print("✅ Password verification SUCCESSFUL")
        else:
            print("❌ Password verification FAILED")
            
        print("=" * 50)

if __name__ == '__main__':
    print("Checking both database configurations...")
    check_database(use_neon=False)  # Check SQLite
    check_database(use_neon=True)   # Check NeonDB
