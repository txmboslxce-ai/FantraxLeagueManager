from flask import render_template, redirect, url_for, flash, request
from app.main import bp
from app.models import Season, Division, Team, TeamSeason, Fixture, CupCompetition, Title, Gameweek, CupRound, Rule
from app.models import ManagerMonth, ManagerOfTheMonth, CupGroup, CupGroupMatch, CupMatch
from app import db
from sqlalchemy import or_, and_
import markdown

@bp.route('/')
@bp.route('/index')
def index():
    current_season = Season.query.filter_by(is_current=True).first()
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
        return render_template('main/index.html', 
                             title='Home',
                             season=current_season,
                             divisions=divisions)
    return render_template('main/index.html', title='Home')

@bp.route('/league_tables')
@bp.route('/league_tables/<int:season_id>')
@bp.route('/league_tables/<int:season_id>/<int:division_id>')
def league_tables(season_id=None, division_id=None):
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
    seasons = Season.query.order_by(Season.start_date.desc()).all()
    
    # Get selected season from query params, default to current season
    selected_season_id = request.args.get('season_id', type=int)
    if selected_season_id:
        selected_season = Season.query.get_or_404(selected_season_id)
    else:
        selected_season = Season.query.filter_by(is_current=True).first()
        if not selected_season and seasons:
            selected_season = seasons[0]
    
    # Get view type (group_stage or knockout)
    view_type = request.args.get('view', 'group_stage')
    
    if not selected_season:
        return render_template(
            'main/cups.html',
            title='Cup Competition',
            seasons=seasons,
            selected_season=None,
            cup=None,
            view_type=view_type,
            message="No season found."
        )
    
    # Find cup competition for the selected season with eager loading and debug info
    cup = CupCompetition.query.options(
        db.joinedload(CupCompetition.rounds).joinedload(CupRound.matches),
        db.joinedload(CupCompetition.groups).joinedload(CupGroup.matches)
    ).filter_by(season_id=selected_season.id).first()
    
    if not cup:
        return render_template(
            'main/cups.html',
            title='Cup Competition',
            seasons=seasons,
            selected_season=selected_season,
            cup=None,
            view_type=view_type,
            message=f"No cup competition found for the {selected_season.name} season. Please create a cup competition in the admin panel."
        )
    
    # Add debug info to see what data we have
    debug_info = f"""
        Cup found:
        - Name: {cup.name}
        - Has Groups: {cup.has_groups}
        - Groups: {len(cup.groups) if cup.groups else 0}
        - Rounds: {len(cup.rounds) if cup.rounds else 0}
    """
    
    if not cup.has_groups and not cup.rounds:
        return render_template(
            'main/cups.html',
            title='Cup Competition',
            seasons=seasons,
            selected_season=selected_season,
            cup=None,
            view_type=view_type,
            message=f"Cup competition exists but has no {view_type} configured yet. {debug_info}"
        )
    
    # Auto-switch to knockout view for non-group stage cups
    if not cup.has_groups and view_type == 'group_stage':
        view_type = 'knockout'
    
    # Load data based on view type
    if view_type == 'group_stage' and cup.has_groups:
        # Handle group stage view
        groups = CupGroup.query.filter_by(competition_id=cup.id).order_by(CupGroup.order).all()
        
        # Update group scores
        for group in groups:
            for match in group.matches:
                if match.home_team_id and match.away_team_id:
                    match.update_scores_from_fixtures()
        db.session.commit()
        
        return render_template(
            'main/cups.html',
            title='Cup Competition',
            seasons=seasons,
            selected_season=selected_season,
            cup=cup,
            view_type=view_type,
            groups=groups
        )
    else:
        # Handle knockout stage view
        rounds = CupRound.query.options(
            db.joinedload(CupRound.matches).joinedload(CupMatch.home_team),
            db.joinedload(CupRound.matches).joinedload(CupMatch.away_team),
            db.joinedload(CupRound.matches).joinedload(CupMatch.winner)
        ).filter_by(competition_id=cup.id).order_by(CupRound.order).all()
        
        # Update match scores
        for round in rounds:
            for match in round.matches:
                if match.home_team_id and match.away_team_id:
                    match.update_scores_from_fixtures()
        db.session.commit()
        
        return render_template(
            'main/cups.html',
            title='Cup Competition',
            seasons=seasons,
            selected_season=selected_season,
            cup=cup,
            view_type='knockout',
            rounds=rounds
        )

@bp.route('/cup/<int:cup_id>')
def cup_detail(cup_id):
    cup = CupCompetition.query.get_or_404(cup_id)
    rounds = CupRound.query.filter_by(competition_id=cup.id).order_by(CupRound.order).all()
    return render_template('main/cups.html', cup=cup, rounds=rounds)

@bp.route('/manager_of_the_month')
def manager_of_the_month():
    """Display Manager of the Month standings with optional month filter."""
    current_season = Season.query.filter_by(is_current=True).first()
    if current_season:
        months = ManagerMonth.query.filter_by(season_id=current_season.id).all()
        
        # Group months by base name (removing division suffix) and organize by division
        month_groups = {}
        for month in months:
            # Extract base name and division (everything after " - ")
            if " - " in month.name:
                base_name = month.name.split(" - ")[0]
                division_name = month.name.split(" - ")[1]
            else:
                base_name = month.name
                division_name = "All"
            
            if base_name not in month_groups:
                month_groups[base_name] = {
                    'base_name': base_name,
                    'divisions': {},
                    'start_gameweek': month.start_gameweek,
                    'end_gameweek': month.end_gameweek
                }
            month_groups[base_name]['divisions'][division_name] = month
        
        # Get selected month group from query params
        month_group_name = request.args.get('month_group')
        selected_month_group = None
        
        if month_group_name and month_group_name in month_groups:
            selected_month_group = month_groups[month_group_name]
        else:
            # Find the latest month group by gameweek number
            latest_group = None
            latest_gameweek = 0
            
            for group_name, group_data in month_groups.items():
                if group_data['end_gameweek'].number > latest_gameweek:
                    latest_group = group_name
                    latest_gameweek = group_data['end_gameweek'].number
            
            if latest_group:
                return redirect(url_for('main.manager_of_the_month', month_group=latest_group))
        
        return render_template('main/motm.html',
                             title='Manager of the Month',
                             month_groups=month_groups,
                             season=current_season,
                             selected_month_group=selected_month_group)
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

@bp.route('/team/<int:team_id>')
def team_profile(team_id):
    from app.models import CupCompetition, CupRound, Title

    team = Team.query.get_or_404(team_id)

    # We'll initialize empty lists here in case there's no current season
    league_titles = []
    cup_titles   = []
    runners_up   = []
    team_season = None

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

        # Get current cup status
        current_cup = CupCompetition.query.filter_by(season_id=current_season.id).first()
        cup_matches = []
        if current_cup:
            # Get all cup matches for this team
            cup_matches = CupMatch.query.join(
                CupRound, CupMatch.round_id == CupRound.id
            ).filter(
                CupRound.competition_id == current_cup.id,
                or_(
                    CupMatch.home_team_id == team.id,
                    CupMatch.away_team_id == team.id
                )
            ).all()

            # Get group stage matches if applicable
            if current_cup.has_groups:
                group_matches = CupGroupMatch.query.join(
                    CupGroup, CupGroupMatch.group_id == CupGroup.id
                ).filter(
                    CupGroup.competition_id == current_cup.id,
                    or_(
                        CupGroupMatch.home_team_id == team.id,
                        CupGroupMatch.away_team_id == team.id
                    )
                ).all()
                cup_matches.extend(group_matches)
    else:
        recent_fixtures = []
        cup_matches = []

    return render_template(
        'main/team_profile.html',
        title=f'{team.name} Profile',
        team=team,
        team_season=team_season,
        league_titles=league_titles,
        cup_titles=cup_titles,
        runners_up=runners_up,
        next_match=next_match,
        fixtures=recent_fixtures,
        cup_matches=cup_matches
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