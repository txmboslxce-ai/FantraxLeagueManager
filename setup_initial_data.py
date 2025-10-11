from datetime import date, datetime, timedelta
from app import create_app, db
from app.models import Season, Division, Team, TeamSeason, Title, CupCompetition, CupRound, CupMatch, ManagerMonth, ManagerOfTheMonth, Fixture, Gameweek

def setup_initial_data():
    app = create_app()
    with app.app_context():
        # Clear all existing data
        CupMatch.query.delete()
        CupRound.query.delete()
        CupCompetition.query.delete()
        ManagerOfTheMonth.query.delete()
        ManagerMonth.query.delete()
        Fixture.query.delete()
        Gameweek.query.delete()
        Title.query.delete()
        TeamSeason.query.delete()
        Team.query.delete()
        Division.query.delete()
        Season.query.delete()
        db.session.commit()

        # Create the current season
        season = Season(
            name='2024/25',
            start_date=date(2024, 8, 1),
            end_date=date(2025, 5, 31),
            is_current=True
        )
        db.session.add(season)
        db.session.flush()  # This assigns the ID to season

        # Create gameweeks
        start_date = datetime(2024, 8, 1)
        for i in range(1, 39):  # 38 gameweeks
            gameweek = Gameweek(
                number=i,
                season_id=season.id,
                deadline=start_date + timedelta(days=7 * (i-1)),
                is_current=False
            )
            db.session.add(gameweek)
        db.session.flush()

        # Create two divisions
        premier = Division(name='Premier Division', season_id=season.id)
        championship = Division(name='Championship', season_id=season.id)
        db.session.add_all([premier, championship])
        db.session.flush()

        # Create teams and assign to divisions
        premier_teams = [
            ("Huss Team - never to be named", "Huss"),
            ("Does it count if only Matip's in?", "Aidan"),
            ("Yacht Partey", "Michael"),
            ("Sons Of Angearchy", "Niall"),
            ("Freedyonfire", "Gary"),
            ("Huss will be missed !", "Eugenio"),
            ("Titanic FC", "Craig"),
            ("Bayern Bru", "David"),
            ("Mee, Myself & Ayew", "Sean"),
            ("Amartey McFly", "Martin"),
            ("Pep and the City", "Kyle"),
            ("Pique Blinders", "Tim"),
        ]

        championship_teams = [
            ("The Mask of Yoro", "Ricky"),
            ("Los Tibbles", "Nick"),
            ("Dunc and disorderly", "Duncan"),
            ("Altrincham Athletic", "Matt TW"),
            ("Chicken Tikka MoSalah", "Rami"),
            ("Onana What's My Name", "Joe"),
            ("Team Name", "Jack"),
            ("Annex Academical", "Karl"),
            ("Okanagan Athletic", "Faraaz"),
            ("Tonali Clips of the Heart", "Matt C"),
            ("Team DycheBall", "Aubrey"),
            ("Leicest We Forget", "Spencer"),
        ]

        # Function to create teams and their season entries
        def create_teams(teams_data, division):
            for team_name, manager_name in teams_data:
                team = Team(name=team_name, manager_name=manager_name)
                db.session.add(team)
                db.session.flush()
                
                # Create TeamSeason entry
                team_season = TeamSeason(
                    team_id=team.id,
                    season_id=season.id,
                    division_id=division.id,
                    points=0,
                    total_score=0.0
                )
                db.session.add(team_season)

        # Create teams for both divisions
        create_teams(premier_teams, premier)
        create_teams(championship_teams, championship)

        # Set current gameweek
        current_gw = Gameweek.query.filter_by(season_id=season.id, number=1).first()
        if current_gw:
            current_gw.is_current = True

        # Commit all changes
        db.session.commit()
        print("Initial data setup completed successfully!")

if __name__ == '__main__':
    setup_initial_data() 