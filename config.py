import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    
    # Get database URL from environment
    db_url = os.environ.get('DATABASE_URL')
    
    if db_url:
        # Handle Heroku-style postgresql:// URLs
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
    else:
        db_url = 'sqlite:///' + os.path.join(basedir, 'fantasy_league.db')
    
    SQLALCHEMY_DATABASE_URI = db_url
    
    print(f"Using database URL: {SQLALCHEMY_DATABASE_URI}")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Only add SSL options for PostgreSQL connections
    if 'postgresql' in db_url:
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_size': 5,
            'max_overflow': 2,
            'pool_timeout': 30,
            'pool_recycle': 1800,
            'connect_args': {
                'ssl': True,
                'ssl_context': True
            }
        }
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_size': 5,
            'max_overflow': 2,
            'pool_timeout': 30,
            'pool_recycle': 1800
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