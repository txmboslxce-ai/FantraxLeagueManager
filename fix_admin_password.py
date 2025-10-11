import os
from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

def fix_admin_password():
    # Set up NeonDB environment
    os.environ['RENDER'] = '1'
    
    # Force reload config
    import config
    from importlib import reload
    reload(config)
    
    # Create app context
    app = create_app(config.Config)
    
    with app.app_context():
        print("Fixing admin password in NeonDB...")
        admin = User.query.filter_by(username='admin').first()
        
        if not admin:
            print("No admin user found!")
            return
            
        # Generate proper password hash using sha256 method
        password = 'fantrax13'
        admin.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        
        try:
            db.session.commit()
            print("✅ Password hash updated successfully")
        except Exception as e:
            print(f"❌ Error updating password: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    fix_admin_password()
