#!/usr/bin/env python3
"""
Script to recalculate TeamSeason totals for the current season only
"""

from app import create_app, db
from app.models import TeamSeason, Season, Fixture, Gameweek
from sqlalchemy import or_

def recalculate_current_season():
    app = create_app()
    
    with app.app_context():
        # Get current season
        current_season = Season.query.filter_by(is_current=True).first()
        if not current_season:
            print("No current season found!")
            return
            
        print(f"Recalculating totals for current season: {current_season.name}")
        
        # Get all team seasons for current season
        team_seasons = TeamSeason.query.filter_by(season_id=current_season.id).all()
        
        print(f"Found {len(team_seasons)} teams in current season")
        
        for ts in team_seasons:
            print(f"\nProcessing team: {ts.team.name}")
            print(f"  Current values: {ts.points} points, {ts.total_score} total score")
            
            # Reset totals
            old_points = ts.points
            old_score = ts.total_score
            ts.points = 0
            ts.total_score = 0.0
            
            # Get all fixtures for this team in current season
            fixtures = Fixture.query.join(
                Gameweek, Fixture.gameweek_id == Gameweek.id
            ).filter(
                Gameweek.season_id == current_season.id,
                or_(
                    Fixture.home_team_id == ts.team_id,
                    Fixture.away_team_id == ts.team_id
                ),
                Fixture.home_score.isnot(None),
                Fixture.away_score.isnot(None)
            ).all()
            
            print(f"  Found {len(fixtures)} played fixtures")
            
            for fixture in fixtures:
                if fixture.home_team_id == ts.team_id:
                    # This team is home
                    ts.total_score += fixture.home_score
                    if fixture.home_score > fixture.away_score:
                        ts.points += 3  # Win
                    elif fixture.home_score == fixture.away_score:
                        ts.points += 1  # Draw
                else:
                    # This team is away
                    ts.total_score += fixture.away_score
                    if fixture.away_score > fixture.home_score:
                        ts.points += 3  # Win
                    elif fixture.away_score == fixture.home_score:
                        ts.points += 1  # Draw
            
            print(f"  New values: {ts.points} points, {ts.total_score} total score")
            if old_points != ts.points or old_score != ts.total_score:
                print(f"  *** UPDATED from {old_points} pts, {old_score} score ***")
        
        # Commit all changes
        db.session.commit()
        print(f"\nAll totals recalculated for season {current_season.name}!")

if __name__ == '__main__':
    recalculate_current_season()