from app import create_app, db
from app.models import ManagerMonth, ManagerOfTheMonth

def create_missing_awards():
    app = create_app()
    with app.app_context():
        # Get all months that have winners
        months = ManagerMonth.query.filter(ManagerMonth.winner_id.isnot(None)).all()
        
        for month in months:
            # Check if award exists
            existing_award = ManagerOfTheMonth.query.filter_by(manager_month_id=month.id).first()
            if not existing_award:
                # Get the standings to get the winner's score
                standings = month.get_standings()
                winner_standing = next((s for s in standings if s['team'].id == month.winner_id), None)
                
                if winner_standing:
                    award = ManagerOfTheMonth(
                        manager_month_id=month.id,
                        team_id=month.winner_id,
                        total_score=winner_standing['goals_for']
                    )
                    db.session.add(award)
                    print(f"Created award for {winner_standing['team'].name} - {month.name}")
        
        db.session.commit()
        print("Finished creating missing awards") 