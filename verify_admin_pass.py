import os
from app import create_app, db
from app.models import User
from werkzeug.security import check_password_hash, generate_password_hash

# Force the use of NeonDB
os.environ['RENDER'] = '1'

app = create_app()

def verify_admin_password():
    with app.app_context():
        # Get the admin user
        admin = User.query.filter_by(username='admin').first()
        
        if not admin:
            print("Admin user not found!")
            return
            
        print(f"Found admin user: {admin.username}")
        print(f"Email: {admin.email}")
        print(f"Current password hash: {admin.password_hash}")
        
        # Try to verify 'fantrax13'
        test_password = 'fantrax13'
        print(f"\nTesting password: {test_password}")
        
        # Generate a new hash for comparison
        new_hash = generate_password_hash(test_password, method='pbkdf2:sha256')
        print(f"Example new hash: {new_hash}")
        
        # Test the password
        if check_password_hash(admin.password_hash, test_password):
            print("Password verification SUCCESSFUL!")
        else:
            print("Password verification FAILED!")
            
            # Set new password hash
            print("\nResetting password hash...")
            admin.password_hash = new_hash
            db.session.commit()
            print("Password hash has been reset.")

if __name__ == '__main__':
    verify_admin_password()
