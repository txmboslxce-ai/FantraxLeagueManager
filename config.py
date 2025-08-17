import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    
    # Get database URL from environment
    db_url = os.environ.get('DATABASE_URL')
    
    if db_url:
        # Replace postgresql:// with postgresql+pg8000:// for the pg8000 driver
        if db_url.startswith('postgresql://'):
            db_url = db_url.replace('postgresql://', 'postgresql+pg8000://', 1)
        elif db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql+pg8000://', 1)
    else:
        db_url = 'sqlite:///' + os.path.join(basedir, 'fantasy_league.db')
    
    # Remove any SSL parameters from the URL as they'll be handled in engine options
    if '?' in db_url:
        db_url = db_url.split('?')[0]
    
    SQLALCHEMY_DATABASE_URI = db_url
    
    print(f"Using database URL: {SQLALCHEMY_DATABASE_URI}")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,
        'max_overflow': 2,
        'pool_timeout': 30,
        'pool_recycle': 1800,
        'connect_args': {
            'ssl_context': True
        },
    }
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=60)

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    # Ensure HTTPS in production
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    
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