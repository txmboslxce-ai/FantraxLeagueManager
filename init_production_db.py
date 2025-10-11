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

def init_database():
    """Initialize the database with essential data if it doesn't exist."""
    try:
        # Create all tables
        db.create_all()
        
        # Check if we have a current season
        current_season = Season.query.filter_by(is_current=True).first()
        
        if not current_season:
            # Create a default season for 2025/26
            new_season = Season(
                name="2025/26",
                start_date=date(2025, 8, 1),
                end_date=date(2026, 5, 31),
                is_current=True
            )
            db.session.add(new_season)
            db.session.commit()
            print("Created default season 2025/26")
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise
    
    if not current_season:
        print("No current season found. Creating default season...")
        
        # Create a default season
        season = Season(
            name='2024/25',
            start_date=date(2024, 8, 1),
            end_date=date(2025, 5, 31),
            is_current=True
        )
        db.session.add(season)
        db.session.flush()
        
        # Create divisions
        premier_league = Division(name='Premier League', season_id=season.id)
        championship = Division(name='Championship', season_id=season.id)
        db.session.add(premier_league)
        db.session.add(championship)
        db.session.flush()
        
        # Create default gameweeks
        for week in range(1, 39):
            gameweek = Gameweek(
                number=week,
                season_id=season.id,
                deadline=datetime(2024, 8, 1),  # Default deadline
                is_current=week == 1
            )
            db.session.add(gameweek)
        
        db.session.commit()
        print(f"Created season: {season.name}")
        print(f"Created divisions: {premier_league.name}, {championship.name}")
        print("Created 38 gameweeks")
    else:
        print(f"Current season found: {current_season.name}")
    
    # Ensure we have a rules entry
    if not Rule.query.first():
        default_rules = Rule(content="Default league rules will be updated by the administrator.")
        db.session.add(default_rules)
        db.session.commit()
        print("Created default rules entry")
    
    print("Database initialization complete!")

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        init_database()
