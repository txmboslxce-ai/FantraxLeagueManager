#!/usr/bin/env python3
"""
Database initialization script for production deployment.
This ensures the database is properly set up with all necessary data.
"""

import os
import sys
from app import create_app, db
from app.models import Season, Division, Team, TeamSeason, Gameweek, Title, Rule
from datetime import datetime, date
from sqlalchemy.exc import SQLAlchemyError

def init_database():
    """Initialize the database with essential data if it doesn't exist."""
    try:
        print("Starting database initialization...")
        
        # Create all tables
        print("Creating database tables...")
        db.create_all()
        
        # Check if we have a current season
        print("Checking for existing season...")
        current_season = Season.query.filter_by(is_current=True).first()
        
        if not current_season:
            print("No current season found. Creating default season...")
            current_season = Season(
                name="2025/26",
                start_date=date(2025, 8, 1),
                end_date=date(2026, 5, 31),
                is_current=True
            )
            db.session.add(current_season)
            
            try:
                db.session.commit()
                print("Successfully created default season 2025/26")
            except SQLAlchemyError as e:
                db.session.rollback()
                print(f"Error committing season: {e}")
                raise
                
            # Create divisions for the new season
            print("Creating divisions...")
            premier_league = Division(name='Premier League', season_id=current_season.id)
            championship = Division(name='Championship', season_id=current_season.id)
            db.session.add(premier_league)
            db.session.add(championship)
            
            # Create gameweeks
            print("Creating gameweeks...")
            for i in range(1, 39):
                gameweek = Gameweek(number=i, season=current_season)
                db.session.add(gameweek)
            
            # Add some basic rules
            print("Adding basic rules...")
            rule1 = Rule(title="Points System", content="Win = 3 points, Draw = 1 point, Loss = 0 points")
            db.session.add(rule1)
            
            try:
                db.session.commit()
                print("Successfully created divisions, gameweeks, and rules")
            except SQLAlchemyError as e:
                db.session.rollback()
                print(f"Error committing additional data: {e}")
                raise
        else:
            print(f"Found existing current season: {current_season.name}")
            
    except Exception as e:
        print(f"Error during database initialization: {e}", file=sys.stderr)
        db.session.rollback()
        raise

if __name__ == '__main__':
    try:
        print("Creating application...")
        app = create_app()
        with app.app_context():
            print("Initializing database...")
            init_database()
            print("Database initialization completed successfully")
    except Exception as e:
        print(f"Fatal error during database initialization: {e}", file=sys.stderr)
        sys.exit(1)