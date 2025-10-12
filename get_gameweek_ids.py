from app import create_app, db
from app.models import Gameweek

app = create_app()
with app.app_context():
    # Get all gameweeks for season 2
    gameweeks = Gameweek.query.filter_by(season_id=2).order_by(Gameweek.number).all()
    
    print("Gameweek Number -> ID mapping:")
    print("----------------------------")
    for gw in gameweeks:
        print(f"Gameweek {gw.number}: ID = {gw.id}")