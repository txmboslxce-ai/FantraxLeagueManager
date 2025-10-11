import os
from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

def check_and_fix_admin(use_neon=True):
    if use_neon:
        os.environ['RENDER'] = '1'
    else:
        if 'RENDER' in os.environ:
            del os.environ['RENDER']
    
    app = create_app()
    
    with app.app_context():
        # Get or create admin user
        admin = User.query.filter_by(username='admin').first()
        
        if not admin:
            print(f"Creating admin user in {'NeonDB' if use_neon else 'SQLite'}")
            admin = User(
                username='admin',
                email='timd_d@icloud.com',
                is_admin=True
            )
            db.session.add(admin)
        else:
            print(f"Found admin user in {'NeonDB' if use_neon else 'SQLite'}")
            admin.email = 'timd_d@icloud.com'  # Ensure email is correct
            admin.is_admin = True  # Ensure admin flag is set
        
        # Set password
        admin.password_hash = generate_password_hash('fantrax13', method='pbkdf2:sha256')
        db.session.commit()
        
        print(f"Database: {'NeonDB' if use_neon else 'SQLite'}")
        print(f"Username: {admin.username}")
        print(f"Email: {admin.email}")
        print(f"Is Admin: {admin.is_admin}")
        print(f"Password Hash: {admin.password_hash}")
        print("--------------------")

if __name__ == '__main__':
    # Check and fix both environments
    print("Checking SQLite (local)...")
    check_and_fix_admin(use_neon=False)
    
    print("\nChecking NeonDB (production)...")
    check_and_fix_admin(use_neon=True)
