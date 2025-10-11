from app import create_app, db
from app.models import User, Season, Division, Team, Gameweek, CupCompetition, CupRound, CupMatch, TeamSeason, Fixture, ManagerMonth, ManagerOfTheMonth, Title
from datetime import date, datetime, timedelta

app = create_app()

with app.app_context():
    # Drop all tables
    db.drop_all()
    
    # Create all tables
    db.create_all()
    
    # Create an admin user
    admin = User(username='admin', email='admin@example.com', is_admin=True)
    admin.set_password('admin')
    db.session.add(admin)
    
    # Create current season
    current_season = Season(
        name='2024/25 Season',
        start_date=date(2024, 8, 1),
        end_date=date(2025, 5, 31),
        is_current=True
    )
    db.session.add(current_season)
    db.session.flush()  # Flush to get the season ID
    
    # Create divisions
    divisions = [
        Division(name='Premier League', season_id=current_season.id),
        Division(name='Championship', season_id=current_season.id)
    ]
    for division in divisions:
        db.session.add(division)
    
    # Create gameweeks (38 gameweeks, one per week starting from season start)
    start_date = datetime(2024, 8, 1, 19, 45)  # 7:45 PM kickoff
    for i in range(1, 39):
        gameweek = Gameweek(
            number=i,
            season_id=current_season.id,
            deadline=start_date + timedelta(days=(i-1)*7),
            is_current=False
        )
        db.session.add(gameweek)
    
    # Set current gameweek
    first_gameweek = Gameweek.query.filter_by(number=1, season_id=current_season.id).first()
    if first_gameweek:
        first_gameweek.is_current = True
    
    # Commit changes
    db.session.commit()
    
    print("Database initialized successfully with initial season data!") 