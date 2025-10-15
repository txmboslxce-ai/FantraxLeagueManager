#!/usr/bin/env python3
"""
Script to recalculate all TeamSeason points and total_score from existing fixtures
"""

from app import create_app, db
from app.models import TeamSeason, Fixture, Gameweek
from sqlalchemy import or_

def recalculate_all_team_totals():
    app = create_app()
    
    with app.app_context():
        print("Recalculating all TeamSeason totals...")
        
        # Get all team seasons
        team_seasons = TeamSeason.query.all()
        
        for ts in team_seasons:
            print(f"Recalculating for team {ts.team.name} in season {ts.season.name}")
            
            # Reset totals
            ts.points = 0
            ts.total_score = 0.0
            
            # Get all fixtures for this team in this season
            fixtures = Fixture.query.join(
                Gameweek, Fixture.gameweek_id == Gameweek.id
            ).filter(
                Gameweek.season_id == ts.season_id,
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
                        print(f"    Win: {fixture.home_score}-{fixture.away_score} (+3 pts)")
                    elif fixture.home_score == fixture.away_score:
                        ts.points += 1  # Draw
                        print(f"    Draw: {fixture.home_score}-{fixture.away_score} (+1 pt)")
                    else:
                        print(f"    Loss: {fixture.home_score}-{fixture.away_score} (+0 pts)")
                else:
                    # This team is away
                    ts.total_score += fixture.away_score
                    if fixture.away_score > fixture.home_score:
                        ts.points += 3  # Win
                        print(f"    Win: {fixture.home_score}-{fixture.away_score} (+3 pts)")
                    elif fixture.away_score == fixture.home_score:
                        ts.points += 1  # Draw
                        print(f"    Draw: {fixture.home_score}-{fixture.away_score} (+1 pt)")
                    else:
                        print(f"    Loss: {fixture.home_score}-{fixture.away_score} (+0 pts)")
            
            print(f"  Final totals: {ts.points} points, {ts.total_score} total score")
            print()
        
        # Commit all changes
        db.session.commit()
        print("All team totals recalculated successfully!")

if __name__ == '__main__':
    recalculate_all_team_totals()