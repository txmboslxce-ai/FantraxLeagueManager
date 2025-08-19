from flask import render_template, redirect, url_for, flash, request
from app.main import bp
from app.models import Season, Division, Team, TeamSeason, Fixture, CupCompetition, Title, Gameweek, CupRound, Rule, ManagerMonth, ManagerOfTheMonth, CupGroup, CupGroupMatch, User
from app import db
from sqlalchemy import or_
import markdown
from datetime import datetime, date
from flask import jsonify

@bp.route('/api/test-db')
def test_db():
    """Test database connection and return status."""
    try:
        # Try to query the seasons table
        season_count = Season.query.count()
        return jsonify({
            'status': 'success',
            'message': 'Database connection successful',
            'season_count': season_count
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def _initialize_database():
    """Initialize database with full league data if empty."""
    try:
        # Check if we need full initialization
        season_count = Season.query.count()
        team_count = Team.query.count()
        
        if season_count == 0 or team_count == 0:
            print("Database is empty, running full data import...")
            
            # Import the full dataset
            import subprocess
            import os
            
            # Get the directory of the current file
            app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            script_path = os.path.join(app_dir, 'full_data_import.py')
            
            # Execute the full import script
            exec(open(script_path).read())
            
            return True
        else:
            print(f"Database already has {season_count} seasons and {team_count} teams")
            return True
            
    except Exception as e:
        print(f"Error during database initialization: {e}")
        # Fallback to basic initialization
        season = Season(
            name='2025/26',
            start_date=date(2025, 8, 1),
            end_date=date(2026, 5, 31),
            is_current=True
        )
        db.session.add(season)
        db.session.flush()
        
        division = Division(name='Premier League', season_id=season.id)
        db.session.add(division)
        db.session.flush()
        
        for week in range(1, 5):
            gameweek = Gameweek(
                number=week,
                season_id=season.id,
                deadline=datetime(2025, 8, 1),
                is_current=week == 1
            )
            db.session.add(gameweek)
        
        rules = Rule(content="Basic league rules. Please update in admin panel.")
        db.session.add(rules)
        
        # Create default admin user
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@fantraxleague.com',
                is_admin=True
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
        
        db.session.commit()
        return True

@bp.route('/')
@bp.route('/index')
def index():
    try:
        current_season = Season.query.filter_by(is_current=True).first()
        
        # If no season exists, initialize the database
        if not current_season:
            _initialize_database()
            current_season = Season.query.filter_by(is_current=True).first()
            
    except Exception as e:
        # Database not initialized yet - return a simple message
        return render_template('main/index.html', 
                             divisions=[], 
                             latest_motm_data={}, 
                             error_message="Database is being initialized. Please refresh in a moment.")
    
    if current_season:
        divisions = Division.query.filter_by(season_id=current_season.id).order_by(
            db.case(
                {
                    'Premier League': 1,
                    'Championship': 2,
                    'League One': 3
                },
                value=Division.name,
                else_=99
            )
        ).all()
        
        # Get latest Manager of the Month data
        latest_motm_month = None
        motm_standings = {}
        
        months = ManagerMonth.query.filter_by(season_id=current_season.id).all()
        if months:
            # Find the latest completed month
            latest_gameweek = 0
            for month in months:
                if month.has_fixtures and month.end_gameweek.number > latest_gameweek:
                    latest_motm_month = month
                    latest_gameweek = month.end_gameweek.number
            
            # Get standings for each division for the latest month
            if latest_motm_month:
                for division in divisions:
                    standings = latest_motm_month.get_standings(division.id)
                    motm_standings[division.id] = standings[:5]  # Top 5 only
        
        return render_template('main/index.html', 
                             title='Home',
                             season=current_season,
                             divisions=divisions,
                             latest_motm_month=latest_motm_month,
                             motm_standings=motm_standings)
    return render_template('main/index.html', title='Home')

@bp.route('/create_admin')
def create_admin():
    """Emergency route to create admin user if none exists."""
    try:
        # Check if admin user exists
        admin_user = User.query.filter_by(username='admin').first()
        if admin_user:
            # Test password to ensure it's working
            test_result = admin_user.check_password('admin123')
            return f"""
            <h2>Admin user already exists!</h2>
            <p><strong>Username:</strong> admin</p>
            <p><strong>Password:</strong> admin123</p>
            <p><strong>Password check:</strong> {'✅ Working' if test_result else '❌ Not working'}</p>
            <p><strong>User ID:</strong> {admin_user.id}</p>
            <p><strong>Is Admin:</strong> {admin_user.is_admin}</p>
            <p><a href='/auth/login' style='background: blue; color: white; padding: 10px; text-decoration: none;'>Login Here</a></p>
            """
        
        # Create new admin user
        admin_user = User(
            username='admin',
            email='admin@fantraxleague.com',
            is_admin=True
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.commit()
        
        # Verify the user was created and password works
        test_user = User.query.filter_by(username='admin').first()
        test_result = test_user.check_password('admin123') if test_user else False
        
        return f"""
        <h2>✅ Admin user created successfully!</h2>
        <p><strong>Username:</strong> admin</p>
        <p><strong>Password:</strong> admin123</p>
        <p><strong>User ID:</strong> {test_user.id if test_user else 'None'}</p>
        <p><strong>Password test:</strong> {'✅ Working' if test_result else '❌ Failed'}</p>
        <p><a href='/auth/login' style='background: blue; color: white; padding: 10px; text-decoration: none;'>Login Here</a></p>
        """
        
    except Exception as e:
        return f"❌ Error creating admin user: {str(e)}<br><br>Stack trace: {repr(e)}"

@bp.route('/league_tables')
@bp.route('/league_tables/<int:season_id>')
@bp.route('/league_tables/<int:season_id>/<int:division_id>')
def league_tables(season_id=None, division_id=None):
    try:
        from flask import current_app
        current_app.logger.info(f"Database URL: {current_app.config['SQLALCHEMY_DATABASE_URI']}")
        
        # Check form parameters first
        form_season_id = request.args.get('season_id', type=int)
        form_division_id = request.args.get('division_id', type=int)
        
        # Form parameters take precedence over URL parameters
        if form_season_id is not None:
            return redirect(url_for('main.league_tables', 
                                  season_id=form_season_id,
                                  division_id=form_division_id))
        
        # Get all seasons for the dropdown, most recent first
        all_seasons = Season.query.order_by(Season.start_date.desc()).all()
        
        # Get current season if no season_id provided
        if season_id is None:
            current_season = Season.query.filter_by(is_current=True).first()
    except Exception as e:
        current_app.logger.error(f"Error in league_tables: {str(e)}")
        return render_template('error.html', error="Error loading league tables")
        if current_season:
            return redirect(url_for('main.league_tables', season_id=current_season.id))
        elif all_seasons:
            return redirect(url_for('main.league_tables', season_id=all_seasons[0].id))
    
    selected_season = None
    divisions = []
    if season_id:
        selected_season = Season.query.get_or_404(season_id)
        
        # Get all divisions ordered correctly
        divisions = Division.query.filter_by(season_id=selected_season.id).order_by(
            db.case(
                {
                    'Premier League': 1,
                    'Championship': 2,
                    'League One': 3
                },
                value=Division.name,
                else_=99
            )
        ).all()
        
        # If no division selected, select Premier League by default
        if division_id is None:
            premier_league = next((d for d in divisions if d.name == 'Premier League'), divisions[0] if divisions else None)
            if premier_league:
                return redirect(url_for('main.league_tables',
                                      season_id=selected_season.id,
                                      division_id=premier_league.id))
        
        selected_division = None
        standings = []
        
        if division_id:
            selected_division = Division.query.get_or_404(division_id)
            if selected_division.season_id != selected_season.id:
                return redirect(url_for('main.league_tables', 
                                      season_id=selected_season.id))
            
            # Get standings for the selected division
            standings = TeamSeason.query.filter_by(
                division_id=selected_division.id,
                season_id=selected_season.id
            ).order_by(
                TeamSeason.points.desc(),
                TeamSeason.total_score.desc()
            ).all()
        
        return render_template('main/league_tables.html',
                             title='League Tables',
                             standings=standings,
                             selected_season=selected_season,
                             selected_division=selected_division,
                             all_seasons=all_seasons,
                             divisions=divisions)
    
    return render_template('main/league_tables.html', 
                         title='League Tables',
                         all_seasons=all_seasons)

@bp.route('/results')
def results():
    # Get all seasons for dropdown, most recent first
    all_seasons = Season.query.order_by(Season.start_date.desc()).all()
    
    # Get season_id from request or use current season
    season_id = request.args.get('season_id', type=int)
    selected_season = None
    
    if season_id:
        selected_season = Season.query.get_or_404(season_id)
    else:
        selected_season = Season.query.filter_by(is_current=True).first() or (all_seasons[0] if all_seasons else None)
    
    if selected_season:
        # Get all gameweeks for dropdown
        gameweeks = Gameweek.query.filter_by(season_id=selected_season.id).order_by(Gameweek.number).all()
        # Get all divisions for dropdown, in correct order
        divisions = Division.query.filter_by(season_id=selected_season.id).order_by(
            db.case(
                {
                    'Premier League': 1,
                    'Championship': 2,
                    'League One': 3
                },
                value=Division.name,
                else_=99
            )
        ).all()
        
        selected_gameweek = request.args.get('gameweek', type=int)
        selected_division_id = request.args.get('division', type=int)
        selected_team_id = request.args.get('team', type=int)

        # Build query
        fixtures_query = Fixture.query.join(Gameweek).filter(Gameweek.season_id == selected_season.id)
        
        # Only completed games (both scores not None)
        fixtures_query = fixtures_query.filter(Fixture.home_score.isnot(None), Fixture.away_score.isnot(None))
        
        if selected_gameweek:
            fixtures_query = fixtures_query.filter(Gameweek.number == selected_gameweek)
        if selected_division_id:
            fixtures_query = fixtures_query.filter(Fixture.division_id == selected_division_id)
        if selected_team_id:
            fixtures_query = fixtures_query.filter(
                or_(Fixture.home_team_id == selected_team_id, Fixture.away_team_id == selected_team_id)
            )

        # Get teams based on selected division
        teams = Team.query.join(TeamSeason).filter(
            TeamSeason.season_id == selected_season.id,
            TeamSeason.division_id == selected_division_id if selected_division_id else True
        ).order_by(Team._name).all()

        # Sort by descending gameweek (most recent first)
        fixtures = fixtures_query.order_by(Gameweek.number.desc(), Fixture.division_id).all()

        return render_template('main/fixtures.html',
            title='Results',
            fixtures=fixtures,
            gameweeks=gameweeks,
            divisions=divisions,
            teams=teams,
            selected_gameweek=selected_gameweek,
            selected_division_id=selected_division_id,
            selected_team_id=selected_team_id,
            season=selected_season,
            all_seasons=all_seasons)
            
    return render_template('main/fixtures.html', 
                         title='Results',
                         all_seasons=all_seasons)

@bp.route('/fixtures')
def fixtures():
    current_season = Season.query.filter_by(is_current=True).first()
    if current_season:
        # Get all gameweeks for dropdown
        gameweeks = Gameweek.query.filter_by(season_id=current_season.id).order_by(Gameweek.number).all()
        # Get all divisions for dropdown, in correct order
        divisions = Division.query.filter_by(season_id=current_season.id).order_by(
            db.case(
                {
                    'Premier League': 1,
                    'Championship': 2,
                    'League One': 3
                },
                value=Division.name,
                else_=99
            )
        ).all()
        
        selected_gameweek = request.args.get('gameweek', type=int)
        selected_division_id = request.args.get('division', type=int)
        selected_team_id = request.args.get('team', type=int)

        # Build query
        fixtures_query = Fixture.query.join(Gameweek).filter(Gameweek.season_id == current_season.id)
        
        # Only upcoming games (either score is None)
        fixtures_query = fixtures_query.filter((Fixture.home_score.is_(None)) | (Fixture.away_score.is_(None)))
        
        if selected_gameweek:
            fixtures_query = fixtures_query.filter(Gameweek.number == selected_gameweek)
        else:
            # Default: start at the next gameweek with any upcoming fixture
            next_gw = Gameweek.query.filter(
                Gameweek.season_id == current_season.id,
                Fixture.query.filter(
                    Fixture.gameweek_id == Gameweek.id,
                    (Fixture.home_score.is_(None)) | (Fixture.away_score.is_(None))
                ).exists()
            ).order_by(Gameweek.number).first()
            if next_gw:
                fixtures_query = fixtures_query.filter(Gameweek.number >= next_gw.number)
        
        if selected_division_id:
            fixtures_query = fixtures_query.filter(Fixture.division_id == selected_division_id)
        if selected_team_id:
            fixtures_query = fixtures_query.filter(
                or_(Fixture.home_team_id == selected_team_id, Fixture.away_team_id == selected_team_id)
            )

        # Get teams based on selected division
        teams = Team.query.join(TeamSeason).filter(
            TeamSeason.season_id == current_season.id,
            TeamSeason.division_id == selected_division_id if selected_division_id else True
        ).order_by(Team._name).all()

        fixtures = fixtures_query.order_by(Gameweek.number.asc(), Fixture.division_id).all()

        return render_template('main/fixtures.html',
            title='Fixtures',
            fixtures=fixtures,
            gameweeks=gameweeks,
            divisions=divisions,
            teams=teams,
            selected_gameweek=selected_gameweek,
            selected_division_id=selected_division_id,
            selected_team_id=selected_team_id,
            season=current_season)
    return render_template('main/fixtures.html', 
                         title='Fixtures')

@bp.route('/cups')
def cups():
    # Get all seasons for the dropdown
    all_seasons = Season.query.order_by(Season.start_date.desc()).all()
    
    # Get selected season from query params, default to current season
    selected_season_id = request.args.get('season_id', type=int)
    if selected_season_id:
        selected_season = Season.query.get_or_404(selected_season_id)
    else:
        selected_season = Season.query.filter_by(is_current=True).first()
        if not selected_season and all_seasons:
            selected_season = all_seasons[0]
    
    # Get view type (group_stage or knockout)
    view_type = request.args.get('view', 'group_stage')
    
    if selected_season:
        # Find cups for the season
        cups = CupCompetition.query.filter_by(season_id=selected_season.id).all()
        
        # Debug logging
        print(f"Looking for cups in season {selected_season.name} (ID: {selected_season.id})")
        print(f"Found {len(cups)} cups for this season")

        # Use the first cup found (we typically only have one per season)
        cup = cups[0] if cups else None

        if cup:
            # Auto-switch to knockout view for previous seasons without groups
            if not cup.has_groups and view_type == 'group_stage' and not selected_season.is_current:
                view_type = 'knockout'
            
            groups = None
            rounds = None
            all_rounds = None
            selected_round_id = None
            
            if cup.has_groups and view_type == 'group_stage':
                # Group stage view
                groups = CupGroup.query.filter_by(competition_id=cup.id).order_by(CupGroup.order).all()
                
                # Update group match scores
                for group in groups:
                    for match in group.matches:
                        match.update_scores_from_fixtures()
                db.session.commit()
                
            elif view_type == 'knockout':
                # Knockout stage view (existing logic)
                all_rounds = CupRound.query.filter_by(
                    competition_id=cup.id
                ).order_by(CupRound.order).all()
                
                selected_round_id = request.args.get('round_id', type=int)
                if selected_round_id:
                    rounds = [CupRound.query.get_or_404(selected_round_id)]
                else:
                    rounds = all_rounds
                
                # ── AUTO-SYNC SCORES ───────────────────────────────────
                for rnd in rounds:
                    # Only process matches that have teams assigned
                    valid_matches = [match for match in rnd.matches if match.home_team_id and match.away_team_id]
                    for match in valid_matches:
                        # clear out any stale values
                        match.first_leg_home_score  = None
                        match.first_leg_away_score  = None
                        match.second_leg_home_score = None
                        match.second_leg_away_score = None
                        # re-pull from the Fixture table based on the assigned gameweeks
                        match.update_scores_from_fixtures()
                db.session.commit()
                # ────────────────────────────────────────────────────────
            
            return render_template(
                'main/cups.html',
                cup=cup,
                groups=groups,
                rounds=rounds,
                all_rounds=all_rounds,
                selected_round_id=selected_round_id,
                all_seasons=all_seasons,
                selected_season=selected_season,
                view_type=view_type
            )
    
    return render_template(
        'main/cups.html',
        cup=None,
        groups=None,
        rounds=None,
        all_rounds=None,
        all_seasons=all_seasons,
        selected_season=selected_season,
        view_type=view_type
    )

@bp.route('/cup/<int:cup_id>')
def cup_detail(cup_id):
    cup = CupCompetition.query.get_or_404(cup_id)
    rounds = CupRound.query.filter_by(competition_id=cup.id).order_by(CupRound.order).all()
    return render_template('main/cups.html', cup=cup, rounds=rounds)

@bp.route('/manager_of_the_month')
def manager_of_the_month():
    current_season = Season.query.filter_by(is_current=True).first()
    if current_season:
        months = ManagerMonth.query.filter_by(season_id=current_season.id).all()
        
        # Get all divisions for the current season (PostgreSQL-compatible)
        division_subquery = db.session.query(TeamSeason.division_id).filter(
            TeamSeason.season_id == current_season.id
        ).distinct().subquery()
        
        divisions = Division.query.filter(
            Division.id.in_(db.session.query(division_subquery.c.division_id))
        ).order_by(
            db.case(
                {
                    'Premier League': 1,
                    'Championship': 2,
                    'League One': 3
                },
                value=Division.name,
                else_=99
            )
        ).all()
        
        # Get selected month and division from query params
        month_id = request.args.get('month_id', type=int)
        division_id = request.args.get('division_id', type=int)
        
        selected_month = None
        selected_division_id = division_id
        
        # Default to first division if none selected
        if not selected_division_id and divisions:
            selected_division_id = divisions[0].id
        
        if month_id:
            selected_month = ManagerMonth.query.get_or_404(month_id)
            if selected_month.season_id != current_season.id:
                return redirect(url_for('main.manager_of_the_month'))
        else:
            # Find the latest month by gameweek number
            latest_month = None
            latest_gameweek = 0
            
            for month in months:
                if month.end_gameweek.number > latest_gameweek:
                    latest_month = month
                    latest_gameweek = month.end_gameweek.number
            
            if latest_month:
                return redirect(url_for('main.manager_of_the_month', 
                                      month_id=latest_month.id, 
                                      division_id=selected_division_id))
        
        return render_template('main/motm.html',
                             title='Manager of the Month',
                             months=months,
                             divisions=divisions,
                             season=current_season,
                             selected_month=selected_month,
                             selected_division_id=selected_division_id)
    return render_template('main/motm.html', title='Manager of the Month')

@bp.route('/motm-winners')
def motm_winners():
    """Display Manager of the Month winners with optional season filter."""
    from app.models import Season
    
    # Get the selected season from query parameters
    season_id = request.args.get('season_id', type=int)
    selected_season = None
    
    # Get all seasons for the dropdown
    seasons = Season.query.order_by(Season.start_date.desc()).all()
    
    # Base query for awards
    awards_query = ManagerOfTheMonth.query.join(
        ManagerMonth
    ).join(
        Season
    )
    
    # Apply season filter if selected
    if season_id:
        selected_season = Season.query.get_or_404(season_id)
        awards_query = awards_query.filter(Season.id == season_id)
    
    # Get ordered awards
    awards = awards_query.order_by(
        Season.start_date.desc(),
        ManagerMonth.start_gameweek_id.desc()
    ).all()
    
    return render_template('main/motm_winners.html',
                         title='Manager of the Month Winners',
                         awards=awards,
                         seasons=seasons,
                         selected_season=selected_season)

def get_team_titles(team_id):
    """Get all titles for a team across all seasons."""
    titles = Title.query.filter_by(team_id=team_id).join(Season).order_by(Season.start_date.desc()).all()
    return {
        'league': [t for t in titles if t.type == 'league' and not t.is_runner_up],
        'cup': [t for t in titles if t.type == 'cup' and not t.is_runner_up],
        'runners_up': [t for t in titles if t.is_runner_up]
    }

@bp.route('/team/<int:team_id>')
def team_profile(team_id):
    from app.models import CupCompetition, CupRound, Title

    team = Team.query.get_or_404(team_id)

    # Debug logging for team profile
    print(f"\nLoading profile for team {team.name} (ID: {team.id})")

    # Get all titles for this team
    titles = get_team_titles(team_id)
    league_titles = titles['league']
    cup_titles = titles['cup']
    runners_up = titles['runners_up']

    print(f"Found titles for team {team.name}:")
    print(f"- League titles: {len(league_titles)}")
    print(f"- Cup titles: {len(cup_titles)}")
    print(f"- Runner-up positions: {len(runners_up)}")

    team_season = None
    
    # Debug - check all titles
    all_titles = Title.query.all()
    print(f"All titles in database: {[f'{t.id}: {t.team_id} - {t.type}' for t in all_titles]}")

    current_season = Season.query.filter_by(is_current=True).first()
    if current_season:
        # Figure out this team's division and position
        team_season = TeamSeason.query.filter_by(
            team_id=team_id,
            season_id=current_season.id
        ).first()

        if team_season:
            # Calculate position in division
            position = TeamSeason.query.filter_by(
                division_id=team_season.division_id,
                season_id=current_season.id
            ).filter(
                (TeamSeason.points > team_season.points) |
                ((TeamSeason.points == team_season.points) & (TeamSeason.total_score > team_season.total_score))
            ).count() + 1
            
            # Update the position in the database
            team_season.position = position
            db.session.commit()

        # ── AUTO-AWARD CUP TITLES ────────────────────────────────────────────
        # Loop every cup this season, find the final, and create missing Title rows
        cup_comps = CupCompetition.query.filter_by(season_id=current_season.id).all()
        for comp in cup_comps:
            final_round = (
                CupRound.query
                .filter_by(competition_id=comp.id)
                .order_by(CupRound.order.desc())
                .first()
            )
            if final_round and getattr(final_round, 'is_complete', False) and final_round.matches:
                final_match = final_round.matches[0]
                winner = final_match.winner
                # runner-up is whichever side didn't win
                loser = (final_match.home_team
                         if final_match.winner_id != final_match.home_team_id
                         else final_match.away_team)

                # create winner title if missing
                if not Title.query.filter_by(
                    team_id=winner.id,
                    season_id=current_season.id,
                    cup_competition_id=comp.id,
                    type='cup',
                    is_runner_up=False
                ).first():
                    db.session.add(Title(
                        team_id=winner.id,
                        season_id=current_season.id,
                        cup_competition_id=comp.id,
                        type='cup',
                        is_runner_up=False
                    ))

                # create runner-up title if missing
                if not Title.query.filter_by(
                    team_id=loser.id,
                    season_id=current_season.id,
                    cup_competition_id=comp.id,
                    type='cup',
                    is_runner_up=True
                ).first():
                    db.session.add(Title(
                        team_id=loser.id,
                        season_id=current_season.id,
                        cup_competition_id=comp.id,
                        type='cup',
                        is_runner_up=True
                    ))
        db.session.commit()
        # ────────────────────────────────────────────────────────────────────

        # Now re-load titles for display
        titles = Title.query.filter_by(team_id=team_id).all()
        league_titles = [t for t in titles if t.type == 'league' and not t.is_runner_up]
        cup_titles   = [t for t in titles if t.type == 'cup'    and not t.is_runner_up]
        runners_up   = [t for t in titles if t.is_runner_up]

    # Get the next match (first unplayed fixture)
    next_match = None
    if team_season:
        next_match = Fixture.query.join(
            Gameweek, Fixture.gameweek_id == Gameweek.id
        ).filter(
            Gameweek.season_id == current_season.id,
            or_(
                Fixture.home_team_id == team.id,
                Fixture.away_team_id == team.id
            ),
            or_(Fixture.home_score.is_(None), Fixture.away_score.is_(None))
        ).order_by(Gameweek.number).first()
        
        # Get last 5 completed fixtures (most recent first)
        recent_fixtures = Fixture.query.join(
            Gameweek, Fixture.gameweek_id == Gameweek.id
        ).filter(
            Gameweek.season_id == current_season.id,
            or_(
                Fixture.home_team_id == team.id,
                Fixture.away_team_id == team.id
            ),
            Fixture.home_score.isnot(None),
            Fixture.away_score.isnot(None)
        ).order_by(Gameweek.number.desc()).limit(5).all()
    else:
        recent_fixtures = []

    return render_template(
        'main/team_profile.html',
        title=f'{team.name} Profile',
        team=team,
        team_season=team_season,
        league_titles=league_titles,
        cup_titles=cup_titles,
        runners_up=runners_up,
        next_match=next_match,
        fixtures=recent_fixtures
    )

@bp.route('/teams')
def teams():
    current_season = Season.query.filter_by(is_current=True).first()
    if current_season:
        divisions = Division.query.filter_by(
            season_id=current_season.id
        ).order_by(
            db.case(
                {
                    'Premier League': 1,
                    'Championship': 2,
                    'League One': 3
                },
                value=Division.name,
                else_=99
            )
        ).all()
        return render_template('main/teams.html',
                             title='Teams',
                             season=current_season,
                             divisions=divisions)
    return render_template('main/teams.html', title='Teams')

@bp.route('/rules')
def rules():
    rule = Rule.query.first()
    html = markdown.markdown(rule.content or '',
                             extensions=['extra','sane_lists']) if rule else ''
    return render_template('main/rules.html', content=html)