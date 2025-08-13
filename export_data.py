#!/usr/bin/env python3
"""
Export database data to SQL format for production import.
This creates a data.sql file that can be used to populate production database.
"""

import os
import sys
from app import create_app, db
from app.models import Season, Division, Team, TeamSeason, Gameweek, Title, Rule, ManagerMonth, ManagerOfTheMonth

def export_data_to_sql():
    """Export current database data to SQL file."""
    
    print("Exporting database to SQL...")
    
    with open('production_data.sql', 'w') as f:
        # Export seasons
        seasons = Season.query.all()
        for season in seasons:
            f.write(f"INSERT INTO season (name, start_date, end_date, is_current) VALUES ('{season.name}', '{season.start_date}', '{season.end_date}', {season.is_current});\n")
        
        # Export divisions
        divisions = Division.query.all()
        for div in divisions:
            f.write(f"INSERT INTO division (name, season_id) VALUES ('{div.name}', (SELECT id FROM season WHERE name = '{div.season.name}'));\n")
        
        # Export teams
        teams = Team.query.all()
        for team in teams:
            f.write(f"INSERT INTO team (name, manager_name) VALUES ('{team.name}', '{team.manager_name}');\n")
        
        # Export gameweeks
        gameweeks = Gameweek.query.all()
        for gw in gameweeks:
            f.write(f"INSERT INTO gameweek (number, season_id, deadline, is_current) VALUES ({gw.number}, (SELECT id FROM season WHERE name = '{gw.season.name}'), '{gw.deadline}', {gw.is_current});\n")
        
        # Export team seasons
        team_seasons = TeamSeason.query.all()
        for ts in team_seasons:
            f.write(f"INSERT INTO team_season (team_id, season_id, division_id, points, games_played, wins, draws, losses, goals_for, goals_against, position) VALUES ((SELECT id FROM team WHERE name = '{ts.team.name}'), (SELECT id FROM season WHERE name = '{ts.season.name}'), (SELECT id FROM division WHERE name = '{ts.division.name}' AND season_id = (SELECT id FROM season WHERE name = '{ts.season.name}')), {ts.points}, {ts.games_played}, {ts.wins}, {ts.draws}, {ts.losses}, {ts.goals_for}, {ts.goals_against}, {ts.position});\n")
        
        # Export manager months
        manager_months = ManagerMonth.query.all()
        for mm in manager_months:
            f.write(f"INSERT INTO manager_month (name, season_id, start_gameweek_id, end_gameweek_id, is_complete) VALUES ('{mm.name}', (SELECT id FROM season WHERE name = '{mm.season.name}'), (SELECT id FROM gameweek WHERE number = {mm.start_gameweek.number} AND season_id = (SELECT id FROM season WHERE name = '{mm.season.name}')), (SELECT id FROM gameweek WHERE number = {mm.end_gameweek.number} AND season_id = (SELECT id FROM season WHERE name = '{mm.season.name}')), {mm.is_complete});\n")
        
        # Export MOTM awards
        motm_awards = ManagerOfTheMonth.query.all()
        for award in motm_awards:
            f.write(f"INSERT INTO manager_of_the_month (manager_month_id, team_id, division_id, points) VALUES ((SELECT id FROM manager_month WHERE name = '{award.manager_month.name}'), (SELECT id FROM team WHERE name = '{award.team.name}'), (SELECT id FROM division WHERE name = '{award.division.name}' AND season_id = {award.division.season_id}), {award.points});\n")
        
        # Export rules
        rules = Rule.query.all()
        for rule in rules:
            content = rule.content.replace("'", "''")  # Escape single quotes
            f.write(f"INSERT INTO rule (content) VALUES ('{content}');\n")
    
    print("✅ Data exported to production_data.sql")
    print("You can use this file to populate the production database")

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        export_data_to_sql()
