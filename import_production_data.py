#!/usr/bin/env python3
"""
Production data import script.
This populates the database with the actual league structure and data.
"""

import os
import sys
from app import create_app, db
from app.models import Season, Division, Team, TeamSeason, Gameweek, Title, Rule, ManagerMonth, ManagerOfTheMonth
from datetime import datetime, date

def import_production_data():
    """Import the actual league data structure."""
    
    print("Starting production data import...")
    
    # Clear existing data
    db.drop_all()
    db.create_all()
    
    # Create seasons
    season_2024 = Season(
        name='2024/25',
        start_date=date(2024, 8, 1),
        end_date=date(2025, 5, 31),
        is_current=False
    )
    
    season_2025 = Season(
        name='2025/26', 
        start_date=date(2025, 8, 1),
        end_date=date(2026, 5, 31),
        is_current=True
    )
    
    db.session.add(season_2024)
    db.session.add(season_2025)
    db.session.flush()
    
    # Create divisions for both seasons
    divisions_2024 = [
        Division(name='Premier League', season_id=season_2024.id),
        Division(name='Championship', season_id=season_2024.id),
        Division(name='League One', season_id=season_2024.id),
        Division(name='League Two', season_id=season_2024.id),
        Division(name='National League', season_id=season_2024.id)
    ]
    
    divisions_2025 = [
        Division(name='Premier League', season_id=season_2025.id),
        Division(name='Championship', season_id=season_2025.id),
        Division(name='League One', season_id=season_2025.id),
        Division(name='League Two', season_id=season_2025.id),
        Division(name='National League', season_id=season_2025.id)
    ]
    
    for div in divisions_2024 + divisions_2025:
        db.session.add(div)
    db.session.flush()
    
    # Create teams (24 teams total)
    team_names = [
        'Arsenal', 'Chelsea', 'Liverpool', 'Manchester City', 'Manchester United', 'Tottenham',
        'Brighton', 'Crystal Palace', 'Everton', 'Fulham', 'Newcastle', 'West Ham',
        'Aston Villa', 'Brentford', 'Burnley', 'Leeds United', 'Leicester City', 'Norwich City',
        'Sheffield United', 'Southampton', 'Watford', 'Wolves', 'Bournemouth', 'Luton Town'
    ]
    
    teams = []
    for i, name in enumerate(team_names):
        team = Team(
            name=name,
            manager_name=f'Manager {i+1}'
        )
        teams.append(team)
        db.session.add(team)
    
    db.session.flush()
    
    # Create gameweeks for both seasons
    for season in [season_2024, season_2025]:
        for week in range(1, 39):
            gameweek = Gameweek(
                number=week,
                season_id=season.id,
                deadline=datetime(2024 if season == season_2024 else 2025, 8, 1),
                is_current=week == 1 and season == season_2025
            )
            db.session.add(gameweek)
    
    db.session.flush()
    
    # Create team-season relationships (distribute teams across divisions)
    # For 2025/26 season (current)
    pl_div = next(d for d in divisions_2025 if d.name == 'Premier League')
    champ_div = next(d for d in divisions_2025 if d.name == 'Championship')
    l1_div = next(d for d in divisions_2025 if d.name == 'League One')
    l2_div = next(d for d in divisions_2025 if d.name == 'League Two')
    nl_div = next(d for d in divisions_2025 if d.name == 'National League')
    
    # Distribute teams (6 in PL, 6 in Championship, 4 in each lower division)
    for i, team in enumerate(teams):
        if i < 6:
            division = pl_div
        elif i < 12:
            division = champ_div
        elif i < 16:
            division = l1_div
        elif i < 20:
            division = l2_div
        else:
            division = nl_div
            
        team_season = TeamSeason(
            team_id=team.id,
            season_id=season_2025.id,
            division_id=division.id,
            points=0,
            games_played=0,
            wins=0,
            draws=0,
            losses=0,
            goals_for=0,
            goals_against=0,
            position=i+1
        )
        db.session.add(team_season)
    
    # Add some sample Manager of the Month awards for 2024/25 season
    # Get 2024/25 divisions
    pl_2024 = next(d for d in divisions_2024 if d.name == 'Premier League')
    champ_2024 = next(d for d in divisions_2024 if d.name == 'Championship')
    l1_2024 = next(d for d in divisions_2024 if d.name == 'League One')
    
    # Create some sample MOTM periods for 2024/25
    gw1 = Gameweek.query.filter_by(season_id=season_2024.id, number=1).first()
    gw4 = Gameweek.query.filter_by(season_id=season_2024.id, number=4).first()
    gw8 = Gameweek.query.filter_by(season_id=season_2024.id, number=8).first()
    
    if gw1 and gw4:
        august_2024 = ManagerMonth(
            name='August 2024',
            season_id=season_2024.id,
            start_gameweek_id=gw1.id,
            end_gameweek_id=gw4.id,
            is_complete=True
        )
        db.session.add(august_2024)
        db.session.flush()
        
        # Add some awards for August 2024
        awards = [
            ManagerOfTheMonth(manager_month_id=august_2024.id, team_id=teams[0].id, division_id=pl_2024.id, points=25),
            ManagerOfTheMonth(manager_month_id=august_2024.id, team_id=teams[6].id, division_id=champ_2024.id, points=22),
            ManagerOfTheMonth(manager_month_id=august_2024.id, team_id=teams[12].id, division_id=l1_2024.id, points=20)
        ]
        for award in awards:
            db.session.add(award)
    
    # Create default rules
    default_rules = Rule(content="""
# League Rules

## General Rules
- Each manager must set their lineup before the gameweek deadline
- Points are awarded based on player performance
- Manager of the Month awards are given for each division

## Scoring System
- Goals: 5 points (6 for defenders/goalkeepers)
- Assists: 3 points
- Clean sheets: 4 points (defenders/goalkeepers)
- Saves: 1 point per 3 saves (goalkeepers)

## Manager of the Month
- Separate competitions for each division
- Awarded monthly based on points accumulated during that period
- Winners receive recognition on the website
    """)
    db.session.add(default_rules)
    
    db.session.commit()
    
    print("✅ Production data import completed!")
    print(f"Created {len(team_names)} teams across 5 divisions")
    print("Created 2 seasons (2024/25 and 2025/26)")
    print("Added sample Manager of the Month data")
    print("Database is ready for use!")

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        import_production_data()
