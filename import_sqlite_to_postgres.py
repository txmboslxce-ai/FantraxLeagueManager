# This script is active and required for data migration
"""One-time (idempotent) import of local SQLite snapshot into the Postgres DATABASE_URL.

Behavior:
- Skips if AUTO_IMPORT env var not set to a truthy value.
- Skips if target engine is SQLite (no migration needed).
- Skips if Season table already has rows (assumes data already present).
- Copies all tables reflected from the SQLite file that also exist in Postgres.

Safe to leave in start sequence; it will become a no-op after first successful import.
"""
import os
import sys
import argparse
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.exc import SQLAlchemyError

from app import create_app, db

TRUTHY = {"1","true","yes","on","y","t"}


def should_run(manual_trigger=False):
    if manual_trigger:
        return True
    auto = os.environ.get("AUTO_IMPORT", "").lower()
    return auto in TRUTHY


def log(msg):
    print(f"[import_sqlite] {msg}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Import SQLite snapshot into Postgres")
    parser.add_argument('--run', action='store_true', help='Run even if AUTO_IMPORT not set')
    parser.add_argument('--force', action='store_true', help='Import even if data already exists (may duplicate)')
    parser.add_argument('--truncate', action='store_true', help='Truncate existing tables before importing (destructive)')
    args = parser.parse_args(argv)

    log(f"Started import script (manual_run={args.run}, force={args.force}, truncate={args.truncate})")

    if not should_run(args.run):
        log("AUTO_IMPORT disabled and --run not provided; skipping.")
        return

    app = create_app()
    with app.app_context():
        target_engine = db.engine
        log(f"Target engine URL: {target_engine.url}")
        if 'sqlite' in str(target_engine.url):
            log("Target DB is SQLite; nothing to import.")
            return

        # Ensure tables exist (migrations should have run in build phase)
        env_force = os.environ.get('FORCE_IMPORT', '').lower() in TRUTHY
        force = args.force or env_force
        try:
            season_count = db.session.execute(text("SELECT COUNT(*) FROM season")).scalar()
            log(f"Existing season rows in target: {season_count}")
            has_data = season_count > 0
        except SQLAlchemyError as e:
            log(f"Cannot query target database (season table missing yet?). Proceeding anyway: {e}")
            has_data = False

        if has_data and not force:
            log("Target already has data; skipping import (use FORCE_IMPORT=true, --force, or truncate).")
            return
        if has_data and force:
            log("FORCE import enabled; proceeding to re-seed (this may duplicate rows unless --truncate).")

        sqlite_path = os.path.join(os.path.dirname(__file__), 'fantasy_league.db')
        if not os.path.exists(sqlite_path):
            log("Local fantasy_league.db not found; nothing to import.")
            return

        source_engine = create_engine(f'sqlite:///{sqlite_path}')
        source_meta = MetaData()
        source_meta.reflect(bind=source_engine)

        target_meta = MetaData()
        target_meta.reflect(bind=target_engine)

        source_conn = source_engine.connect()
        target_conn = target_engine.connect()
        trans = target_conn.begin()
        try:
            # Try relaxing constraints for faster load (Postgres only)
            try:
                target_conn.execute(text('SET session_replication_role = replica;'))
            except Exception:
                pass

            if has_data and force and args.truncate:
                # Truncate all target tables we will populate (simple order: reverse dependency not handled; rely on CASCADE)
                try:
                    log("Truncating existing tables (cascade)...")
                    target_conn.execute(text('TRUNCATE TABLE ' + ', '.join([t.name for t in target_meta.sorted_tables if t.name in source_meta.tables]) + ' CASCADE;'))
                except Exception as e:
                    log(f"Truncate failed (continuing): {e}")

            for table in source_meta.sorted_tables:
                if table.name not in target_meta.tables:
                    continue
                log(f"Preparing to copy table {table.name}")
                rows = source_conn.execute(table.select()).mappings().all()
                if not rows:
                    continue
                target_table = target_meta.tables[table.name]
                target_conn.execute(target_table.insert(), rows)
                log(f"Copied {len(rows)} rows into {table.name}")

            try:
                target_conn.execute(text('SET session_replication_role = DEFAULT;'))
            except Exception:
                pass
            trans.commit()
            log("Import completed successfully.")
        except Exception as e:
            trans.rollback()
            log(f"Import failed: {e}")
        finally:
            source_conn.close()
            target_conn.close()


if __name__ == '__main__':
    main()
