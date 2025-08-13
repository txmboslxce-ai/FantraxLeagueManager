#!/usr/bin/env python3
"""
One-time data import for production deployment.
This will populate the database with the full league structure.
"""

import os
import sys
from app import create_app, db
from app.models import Season, Division, Team, TeamSeason, Gameweek, Title, Rule, ManagerMonth, ManagerOfTheMonth
from datetime import datetime, date

def import_full_data():
    """Import complete league data matching your local setup."""
    
    print("Starting full data import...")
    
    # Clear any existing data
    try:
        db.session.execute("DELETE FROM manager_of_the_month")
        db.session.execute("DELETE FROM manager_month") 
        db.session.execute("DELETE FROM team_season")
        db.session.execute("DELETE FROM gameweek")
        db.session.execute("DELETE FROM division")
        db.session.execute("DELETE FROM team")
        db.session.execute("DELETE FROM season")
        db.session.execute("DELETE FROM rule")
        db.session.commit()
    except:
        db.session.rollback()
    
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
    db.session.commit()
    
    # Create divisions for both seasons
    divisions_2024 = []
    divisions_2025 = []
    
    for season, div_list in [(season_2024, divisions_2024), (season_2025, divisions_2025)]:
        for div_name in ['Premier League', 'Championship', 'League One', 'League Two', 'National League']:
            division = Division(name=div_name, season_id=season.id)
            db.session.add(division)
            div_list.append(division)
    
    db.session.commit()
    
    # Create teams (24 teams)
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
    
    db.session.commit()
    
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
    
    db.session.commit()
    
    # Create team-season relationships for 2025/26 (current season)
    # Distribute teams: 6 in PL, 6 in Championship, 4 in each lower division
    current_divisions = divisions_2025
    
    for i, team in enumerate(teams):
        if i < 6:
            division = current_divisions[0]  # Premier League
        elif i < 12:
            division = current_divisions[1]  # Championship
        elif i < 16:
            division = current_divisions[2]  # League One
        elif i < 20:
            division = current_divisions[3]  # League Two
        else:
            division = current_divisions[4]  # National League
            
        team_season = TeamSeason(
            team_id=team.id,
            season_id=season_2025.id,
            division_id=division.id,
            points=0,
            total_score=0.0,
            position=i+1
        )
        db.session.add(team_season)
    
    db.session.commit()
    
    # Create sample Manager of the Month data for 2024/25
    gw1_2024 = Gameweek.query.filter_by(season_id=season_2024.id, number=1).first()
    gw4_2024 = Gameweek.query.filter_by(season_id=season_2024.id, number=4).first()
    gw8_2024 = Gameweek.query.filter_by(season_id=season_2024.id, number=8).first()
    gw12_2024 = Gameweek.query.filter_by(season_id=season_2024.id, number=12).first()
    
    # August 2024
    august_2024 = ManagerMonth(
        name='August 2024',
        season_id=season_2024.id,
        start_gameweek_id=gw1_2024.id,
        end_gameweek_id=gw4_2024.id
    )
    db.session.add(august_2024)
    
    # September 2024
    september_2024 = ManagerMonth(
        name='September 2024',
        season_id=season_2024.id,
        start_gameweek_id=gw4_2024.id + 1,
        end_gameweek_id=gw8_2024.id
    )
    db.session.add(september_2024)
    
    # October 2024
    october_2024 = ManagerMonth(
        name='October 2024',
        season_id=season_2024.id,
        start_gameweek_id=gw8_2024.id + 1,
        end_gameweek_id=gw12_2024.id
    )
    db.session.add(october_2024)
    
    db.session.commit()
    
    # Create MOTM awards for 2024/25 season
    pl_2024 = next(d for d in divisions_2024 if d.name == 'Premier League')
    champ_2024 = next(d for d in divisions_2024 if d.name == 'Championship')
    l1_2024 = next(d for d in divisions_2024 if d.name == 'League One')
    
    # August awards
    awards_august = [
        ManagerOfTheMonth(manager_month_id=august_2024.id, team_id=teams[0].id, division_id=pl_2024.id, points=28),
        ManagerOfTheMonth(manager_month_id=august_2024.id, team_id=teams[6].id, division_id=champ_2024.id, points=25),
        ManagerOfTheMonth(manager_month_id=august_2024.id, team_id=teams[12].id, division_id=l1_2024.id, points=23)
    ]
    
    # September awards  
    awards_september = [
        ManagerOfTheMonth(manager_month_id=september_2024.id, team_id=teams[1].id, division_id=pl_2024.id, points=26),
        ManagerOfTheMonth(manager_month_id=september_2024.id, team_id=teams[7].id, division_id=champ_2024.id, points=24),
        ManagerOfTheMonth(manager_month_id=september_2024.id, team_id=teams[13].id, division_id=l1_2024.id, points=22)
    ]
    
    # October awards
    awards_october = [
        ManagerOfTheMonth(manager_month_id=october_2024.id, team_id=teams[2].id, division_id=pl_2024.id, points=27),
        ManagerOfTheMonth(manager_month_id=october_2024.id, team_id=teams[8].id, division_id=champ_2024.id, points=26),
        ManagerOfTheMonth(manager_month_id=october_2024.id, team_id=teams[14].id, division_id=l1_2024.id, points=24)
    ]
    
    for award in awards_august + awards_september + awards_october:
        db.session.add(award)
    
    # Create rules
    rules_content = """
# Fantasy Premier League Rules

## General Rules
- Each manager must set their lineup before the gameweek deadline
- Points are awarded based on player performance in real Premier League matches
- Manager of the Month awards are given for each division separately

## Scoring System
- **Goals**: 5 points (6 points for defenders and goalkeepers)
- **Assists**: 3 points
- **Clean Sheets**: 4 points (defenders and goalkeepers only)
- **Saves**: 1 point per 3 saves (goalkeepers only)
- **Yellow Cards**: -1 point
- **Red Cards**: -3 points
- **Own Goals**: -2 points
- **Penalties Missed**: -2 points

## Manager of the Month
- Separate competitions for each division (Premier League, Championship, League One, League Two, National League)
- Awarded monthly based on total points accumulated during that calendar month
- Winners receive recognition on the website and league history
- Points are calculated from all gameweeks within the month period

## Divisions
- **Premier League**: Top tier (6 teams)
- **Championship**: Second tier (6 teams) 
- **League One**: Third tier (4 teams)
- **League Two**: Fourth tier (4 teams)
- **National League**: Fifth tier (4 teams)

## Admin Contact
For any questions or disputes, contact the league administrator.
    """
    
    rules = Rule(content=rules_content.strip())
    db.session.add(rules)
    
    db.session.commit()
    
    print("✅ Full data import completed successfully!")
    print(f"Created:")
    print(f"  - 2 seasons (2024/25, 2025/26)")
    print(f"  - 24 teams across 5 divisions")
    print(f"  - 38 gameweeks per season")
    print(f"  - 3 Manager of the Month periods with 9 awards")
    print(f"  - Complete league rules")
    print("Database is fully populated and ready for use!")

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        import_full_data()
