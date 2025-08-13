from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os

# Use Bootstrap4 in production, Bootstrap in development
if os.environ.get('FLASK_ENV') == 'production':
    from flask_bootstrap import Bootstrap4 as BootstrapClass
else:
    from flask_bootstrap import Bootstrap as BootstrapClass

from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
bootstrap = BootstrapClass()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bootstrap.init_app(app)
    
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
    # Ensure at least one admin user exists (for fresh deployments)
    from app.models import User
    with app.app_context():
        try:
            if User.query.filter_by(is_admin=True).first() is None:
                default_admin = User(username='admin', email='admin@example.com', is_admin=True)
                default_admin.set_password(os.environ.get('DEFAULT_ADMIN_PASSWORD', 'admin'))
                db.session.add(default_admin)
                db.session.commit()
        except Exception:
            # Database might not be initialized yet (e.g., before migrations); ignore silently
            pass

        # Attempt inline data import if using Postgres and tables are empty and AUTO_IMPORT is set.
        try:
            from sqlalchemy import text, create_engine, MetaData
            truthy = {"1","true","yes","on","y","t"}
            if os.environ.get('AUTO_IMPORT','').lower() in truthy:
                # Only proceed if target is Postgres and key tables empty
                if 'postgres' in str(db.engine.url):
                    season_count = 0
                    team_count = 0
                    try:
                        season_count = db.session.execute(text('SELECT COUNT(*) FROM season')).scalar() or 0
                    except Exception:
                        pass
                    try:
                        team_count = db.session.execute(text('SELECT COUNT(*) FROM team')).scalar() or 0
                    except Exception:
                        pass
                    print(f"[inline-import] season_count={season_count} team_count={team_count}")
                    if season_count == 0 or team_count == 0:
                        sqlite_path = os.path.join(os.path.dirname(__file__), '..', 'fantasy_league.db')
                        sqlite_path = os.path.abspath(sqlite_path)
                        print(f"[inline-import] sqlite_path={sqlite_path} exists={os.path.exists(sqlite_path)}")
                        if os.path.exists(sqlite_path):
                            print('[inline-import] Starting inline import from fantasy_league.db')
                            source_engine = create_engine(f'sqlite:///{sqlite_path}')
                            source_meta = MetaData()
                            source_meta.reflect(bind=source_engine)
                            target_meta = MetaData()
                            target_meta.reflect(bind=db.engine)
                            source_conn = source_engine.connect()
                            target_conn = db.engine.connect()
                            trans = target_conn.begin()
                            try:
                                for table in source_meta.sorted_tables:
                                    if table.name not in target_meta.tables:
                                        continue
                                    rows = source_conn.execute(table.select()).mappings().all()
                                    if not rows:
                                        continue
                                    target_table = target_meta.tables[table.name]
                                    target_conn.execute(target_table.insert(), rows)
                                    print(f'[inline-import] Copied {len(rows)} rows into {table.name}')
                                trans.commit()
                                print('[inline-import] Import complete')
                            except Exception as e:
                                trans.rollback()
                                print('[inline-import] Import failed', e)
                            finally:
                                source_conn.close()
                                target_conn.close()
        except Exception as e:
            print('[inline-import] Skipped due to error:', e)

    return app

from app import models 