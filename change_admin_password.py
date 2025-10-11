from app import create_app, db
from app.models import User
import getpass

def change_admin_password():
    app = create_app()
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("Error: Admin user not found!")
            return
        
        new_password = getpass.getpass("Enter new admin password: ")
        confirm_password = getpass.getpass("Confirm new admin password: ")
        
        if new_password != confirm_password:
            print("Error: Passwords do not match!")
            return
        
        admin.set_password(new_password)
        db.session.commit()
        print("Admin password successfully changed!")

if __name__ == '__main__':
    change_admin_password()
