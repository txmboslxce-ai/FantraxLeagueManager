from dotenv import load_dotenv
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap4
from config import Config

# Load environment variables from .env file
load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
bootstrap = Bootstrap4()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bootstrap.init_app(app)
    
    if app.debug:
        # Add detailed error logging in debug mode
        import logging
        from logging.handlers import RotatingFileHandler
        import os
        
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/fantrax.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Fantrax League Manager startup')
    
    if not os.environ.get('RENDER'):
        # Only auto-create tables in development
        with app.app_context():
            db.create_all()
            
            # Check if we have any seasons
            from app.models import Season, User
            if not Season.query.first():
                from datetime import date
                # Create a default season
                season = Season(
                    name='2025/26',
                    start_date=date(2025, 8, 1),
                    end_date=date(2026, 5, 31),
                    is_current=True
                )
                db.session.add(season)
                
                # Create admin user if it doesn't exist
                if not User.query.filter_by(username='admin').first():
                    admin = User(username='admin', 
                               email='admin@example.com',
                               is_admin=True)
                    admin.set_password('admin123')
                    db.session.add(admin)
                
                db.session.commit()
    
    # Register template filters
    from app.template_filters import init_template_filters
    init_template_filters(app)
    
    # Register blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    return app

from app import models 