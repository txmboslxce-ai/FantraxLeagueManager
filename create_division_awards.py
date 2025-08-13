from app import create_app, db
from app.models import ManagerMonth, ManagerOfTheMonth, Division, TeamSeason, Team, Fixture, Gameweek
from sqlalchemy import or_, and_

def create_division_awards():
    app = create_app()
    with app.app_context():
        # Get all existing months
        months = ManagerMonth.query.all()
        
        for month in months:
            print(f"\nProcessing month: {month.name} ({month.season.name})")
            
            # Get all divisions that have teams playing in this month
            divisions = Division.query.join(
                TeamSeason, TeamSeason.division_id == Division.id
            ).join(
                Team, TeamSeason.team_id == Team.id
            ).join(
                Fixture, or_(
                    Fixture.home_team_id == Team.id,
                    Fixture.away_team_id == Team.id
                )
            ).join(
                Gameweek, Fixture.gameweek_id == Gameweek.id
            ).filter(
                Gameweek.season_id == month.season_id,
                Gameweek.number >= month.start_gameweek.number,
                Gameweek.number <= month.end_gameweek.number,
                Fixture.home_score.isnot(None),
                Fixture.away_score.isnot(None),
                TeamSeason.season_id == month.season_id
            ).distinct().all()
            
            print(f"Found {len(divisions)} divisions with fixtures")
            
            # Remove existing awards for this month (we'll recreate them properly)
            existing_awards = ManagerOfTheMonth.query.filter_by(manager_month_id=month.id).all()
            for award in existing_awards:
                print(f"  Removing existing award: {award.team.name}")
                db.session.delete(award)
            
            # Create new division-specific awards
            for division in divisions:
                standings = month.get_standings(division.id)
                if standings:
                    winner = standings[0]['team']
                    
                    # Create the ManagerOfTheMonth record for this division
                    award = ManagerOfTheMonth(
                        manager_month_id=month.id,
                        team_id=winner.id,
                        division_id=division.id,
                        total_score=standings[0]['goals_for']
                    )
                    db.session.add(award)
                    print(f"  Created award: {winner.name} ({division.name}) - {standings[0]['goals_for']:.2f} PF")
                else:
                    print(f"  No standings found for {division.name}")
        
        # Commit all changes
        db.session.commit()
        print("\nFinished creating division-specific awards!")

if __name__ == '__main__':
    create_division_awards()
