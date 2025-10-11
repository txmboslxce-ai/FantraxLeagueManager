import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    
    # Database configuration
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=60)
    
    # Set up the database path
    if os.environ.get('RENDER'):
        # On Render.com, use a path in the persistent disk
        db_path = '/opt/render/project/src/fantasy_league.db'
    else:
        # Local development
        db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'fantasy_league.db')
    
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'
    
    @staticmethod
    def init_app(app):
        # Ensure the database directory exists
        db_dir = os.path.dirname(Config.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', ''))
        os.makedirs(db_dir, exist_ok=True)
        
        # Ensure the database file is writable
        if os.environ.get('RENDER'):
            db_file = Config.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')
            if not os.path.exists(db_file):
                open(db_file, 'a').close()
            os.chmod(db_file, 0o666)
    
class DevelopmentConfig(Config):
    DEBUG = True
    
class ProductionConfig(Config):
    DEBUG = False
    
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 