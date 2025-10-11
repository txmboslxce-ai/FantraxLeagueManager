import os
from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

# Force the use of NeonDB
os.environ['RENDER'] = '1'

app = create_app()

def fix_admin_account():
    with app.app_context():
        # Get the admin user
        admin = User.query.filter_by(username='admin').first()
        
        if not admin:
            print("Admin user not found!")
            return
            
        # Update email and password
        admin.email = 'timd_d@icloud.com'
        admin.password_hash = generate_password_hash('fantrax13', method='pbkdf2:sha256')
        db.session.commit()
        
        print("Admin account has been updated:")
        print("Username: admin")
        print("Email: timd_d@icloud.com")
        print("Password: fantrax13")
        print("\nTry logging in with these credentials now.")

if __name__ == '__main__':
    fix_admin_account()
