from flask import render_template, redirect, url_for, flash, request, jsonify
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import or_
from app import db
from app.admin import bp
from app.admin.forms import (DivisionForm, TeamForm, EditTeamForm, BulkFixtureForm, ScoreUploadForm,
                           CupCompetitionForm, CupRoundForm, CupMatchForm,
                           CupGroupTeamForm, CupGroupMatchForm, EditCupGroupMatchForm,
                           ManagerMonthForm, SeasonForm, EditSeasonForm, EndSeasonForm, RulesForm,
                           TitleForm)
from app.models import (Division, Team, TeamSeason, Fixture, CupCompetition,
                       CupRound, CupMatch, CupGroup, CupGroupTeam, CupGroupMatch,
                       ManagerMonth, ManagerOfTheMonth,
                       Season, Title, Gameweek, Rule)
from functools import wraps
from app.admin.decorators import admin_required
from datetime import datetime, date
from app.utils import normalize_team_name

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need to be an admin to access this page.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    current_season = Season.query.filter_by(is_current=True).first()
    return render_template('admin/dashboard.html', title='Admin Dashboard',
                         season=current_season)

@bp.route('/title/<int:title_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_title(title_id):
    title = Title.query.get_or_404(title_id)
    team_id = title.team_id
    db.session.delete(title)
    db.session.commit()
    flash('Title deleted successfully.', 'success')
    return redirect(url_for('admin.manage_team_titles', team_id=team_id))

@bp.route('/team/<int:team_id>/titles', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_team_titles(team_id):
    team = Team.query.get_or_404(team_id)
    form = TitleForm()
    
    # Load choices for dropdowns
    form.season_id.choices = [(s.id, s.name) for s in Season.query.order_by(Season.start_date.desc()).all()]
    form.division_id.choices = [(d.id, d.name) for d in Division.query.all()]
    
    if form.validate_on_submit():
        title = Title(
            team_id=team_id,
            season_id=form.season_id.data,
            type=form.type.data,
            division_id=form.division_id.data if form.type.data == 'league' else None,
            is_runner_up=form.is_runner_up.data
        )
        db.session.add(title)
        db.session.commit()
        flash(f'Title added for {team.name}!', 'success')
        return redirect(url_for('admin.manage_team_titles', team_id=team_id))
    
    titles = Title.query.filter_by(team_id=team_id).order_by(Title.season_id.desc()).all()
    return render_template('admin/team_titles.html', title=f'Manage {team.name} Titles',
                         team=team, form=form, titles=titles)

@bp.route('/divisions', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_divisions():
    form = DivisionForm()
    if form.validate_on_submit():
        current_season = Season.query.filter_by(is_current=True).first()
        if current_season:
            division = Division(name=form.name.data, season_id=current_season.id)
            db.session.add(division)
            db.session.commit()
            flash(f'Division {division.name} has been created!', 'success')
            return redirect(url_for('admin.manage_divisions'))
        flash('No active season found!', 'danger')
    
    current_season = Season.query.filter_by(is_current=True).first()
    divisions = []
    if current_season:
        divisions = Division.query.filter_by(season_id=current_season.id).all()
    
    return render_template('admin/divisions.html', title='Manage Divisions',
                         form=form, divisions=divisions)

@bp.route('/teams', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_teams():
    form = TeamForm()
    current_season = Season.query.filter_by(is_current=True).first()
    if current_season:
        divisions = Division.query.filter_by(season_id=current_season.id).all()
        form.division_id.choices = [(d.id, d.name) for d in divisions]
        
        if form.validate_on_submit():
            team = Team(name=form.name.data, manager_name=form.manager_name.data)
            db.session.add(team)
            db.session.flush()
            
            team_season = TeamSeason(
                team_id=team.id,
                season_id=current_season.id,
                division_id=form.division_id.data
            )
            db.session.add(team_season)
            db.session.commit()
            
            flash(f'Team {team.name} has been created!', 'success')
            return redirect(url_for('admin.manage_teams'))
    
    teams = Team.query.all()
    return render_template('admin/teams.html', title='Manage Teams',
                         form=form, teams=teams)

@bp.route('/team/<int:team_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_team(team_id):
    team = Team.query.get_or_404(team_id)
    
    # Check if team has any fixtures with scores - prevent deletion if they do
    fixtures_with_scores = Fixture.query.filter(
        or_(
            Fixture.home_team_id == team_id,
            Fixture.away_team_id == team_id
        ),
        Fixture.home_score.isnot(None),
        Fixture.away_score.isnot(None)
    ).count()
    
    if fixtures_with_scores > 0:
        flash(f'Cannot delete {team.name} - team has played matches with scores. Please remove scores first.', 'danger')
        return redirect(url_for('admin.manage_teams'))
    
    # Delete related records in the correct order
    try:
        # Delete titles
        Title.query.filter_by(team_id=team_id).delete()
        
        # Delete Manager of the Month awards
        ManagerOfTheMonth.query.filter_by(team_id=team_id).delete()
        
        # Delete cup match references
        CupMatch.query.filter_by(home_team_id=team_id).update({'home_team_id': None})
        CupMatch.query.filter_by(away_team_id=team_id).update({'away_team_id': None})
        CupMatch.query.filter_by(winner_id=team_id).update({'winner_id': None})
        
        # Delete fixtures without scores
        Fixture.query.filter(
            or_(
                Fixture.home_team_id == team_id,
                Fixture.away_team_id == team_id
            ),
            Fixture.home_score.is_(None),
            Fixture.away_score.is_(None)
        ).delete()
        
        # Delete team seasons
        TeamSeason.query.filter_by(team_id=team_id).delete()
        
        # Delete the team
        db.session.delete(team)
        db.session.commit()
        
        flash(f'Team {team.name} has been deleted!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting team: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_teams'))

@bp.route('/team/<int:team_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_team(team_id):
    from app.admin.forms import EditTeamForm
    team = Team.query.get_or_404(team_id)
    form = EditTeamForm()
    
    if form.validate_on_submit():
        team.name = form.name.data
        team.manager_name = form.manager_name.data
        db.session.commit()
        flash(f'Team {team.name} has been updated!', 'success')
        return redirect(url_for('admin.manage_teams'))
    elif request.method == 'GET':
        form.name.data = team.name
        form.manager_name.data = team.manager_name
    
    return render_template('admin/edit_team.html', title='Edit Team', form=form, team=team)

@bp.route('/fixtures', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_fixtures():
    from flask import current_app, request
    import traceback
    
    def log_error(e, context=""):
        error_msg = f'Error in manage_fixtures {context}: {str(e)}'
        current_app.logger.error(error_msg)
        if current_app.debug:
            current_app.logger.error(traceback.format_exc())
        return error_msg
    
    form = BulkFixtureForm()
    
    try:
        # Log request details in debug mode
        if current_app.debug and request.method == 'POST':
            current_app.logger.info(f'POST data: {request.form.to_dict()}')
            
        current_season = Season.query.filter_by(is_current=True).first()
        if not current_season:
            error_msg = "No current season found. Please create a season first."
            log_error(error_msg)
            flash(error_msg, 'warning')
            return redirect(url_for('admin.manage_seasons'))

        # Get divisions for the form
        divisions = Division.query.filter_by(season_id=current_season.id).all()
        if not divisions:
            error_msg = "No divisions found for the current season. Please create a division first."
            log_error(error_msg)
            flash(error_msg, 'warning')
            return redirect(url_for('admin.manage_divisions'))
            
        form.division_id.choices = [(d.id, d.name) for d in divisions]
        
        if form.validate_on_submit():
            if not form.division_id.data:
                flash('Please select a division', 'danger')
                return redirect(url_for('admin.manage_fixtures'))

            # Validate division exists
            division = Division.query.get(form.division_id.data)
            if not division:
                flash('Selected division does not exist', 'danger')
                return redirect(url_for('admin.manage_fixtures'))

            success_count = 0
            error_count = 0
            fixtures_text = form.fixtures_text.data.strip().split('\n')
            
            # Verify gameweeks exist
            all_gameweeks = Gameweek.query.filter_by(season_id=current_season.id).all()
            gameweeks = {gw.number: gw for gw in all_gameweeks}
            
            if not gameweeks:
                error_msg = "No gameweeks found for the current season."
                log_error(error_msg)
                flash(error_msg, 'danger')
                return redirect(url_for('admin.manage_fixtures'))
                
            # Log available gameweeks
            available_numbers = sorted([gw.number for gw in all_gameweeks])
            current_app.logger.info(f'Available gameweek numbers: {available_numbers}')

            # Get all teams for lookup
            all_teams = {normalize_team_name(team.name): team for team in Team.query.all()}
            
            try:
                for fixture_line in fixtures_text:
                    if not fixture_line.strip():
                        continue
                        
                    parts = [p.strip() for p in fixture_line.split('\t') if p.strip()]
                    
                    if len(parts) != 3:
                        error_msg = f'Invalid line format: {fixture_line}'
                        log_error(error_msg)
                        flash(error_msg, 'danger')
                        error_count += 1
                        continue

                    try:
                        gameweek_number = int(parts[0])
                        if gameweek_number < 1 or gameweek_number > 38:
                            error_msg = f'Invalid gameweek number {gameweek_number}. Must be between 1 and 38.'
                            log_error(error_msg)
                            flash(error_msg, 'danger')
                            error_count += 1
                            continue

                        home_team_name = normalize_team_name(parts[1])
                        away_team_name = normalize_team_name(parts[2])
                        
                        gameweek = gameweeks.get(gameweek_number)
                        if not gameweek:
                            error_msg = f'Could not find gameweek {gameweek_number} in the database. Available gameweeks: {sorted(gameweeks.keys())}'
                            log_error(error_msg)
                            flash(error_msg, 'danger')
                            error_count += 1
                            continue

                        home_team = all_teams.get(home_team_name)
                        away_team = all_teams.get(away_team_name)
                        
                        if not home_team or not away_team:
                            if not home_team:
                                error_msg = f'Could not find home team: "{parts[1]}"'
                                log_error(error_msg)
                                flash(error_msg, 'danger')
                            if not away_team:
                                error_msg = f'Could not find away team: "{parts[2]}"'
                                log_error(error_msg)
                                flash(error_msg, 'danger')
                            error_count += 1
                            continue

                        # Check for existing fixture
                        existing = Fixture.query.filter_by(
                            gameweek_id=gameweek.id,
                            home_team_id=home_team.id,
                            away_team_id=away_team.id
                        ).first()
                        
                        if existing:
                            error_msg = f'Fixture already exists: GW{gameweek_number} - {parts[1]} vs {parts[2]}'
                            log_error(error_msg)
                            flash(error_msg, 'warning')
                            error_count += 1
                            continue

                        # Add debug logging
                        current_app.logger.info(f'Creating fixture: GW={gameweek.id}, Home={home_team.id}, Away={away_team.id}, Div={form.division_id.data}')
                        
                        try:
                            # Find the correct gameweek by number
                            correct_gameweek = gameweeks.get(gameweek_number)
                            if not correct_gameweek:
                                error_msg = f'Could not find gameweek number {gameweek_number}'
                                log_error(error_msg)
                                flash(error_msg, 'danger')
                                error_count += 1
                                continue

                            fixture = Fixture(
                                gameweek_id=correct_gameweek.id,  # Use the correct gameweek's ID
                                home_team_id=home_team.id,
                                away_team_id=away_team.id,
                                division_id=form.division_id.data
                            )
                            db.session.add(fixture)
                            db.session.flush()  # Try to flush to catch any database errors early
                            success_count += 1
                        except Exception as e:
                            error_msg = f'Error creating fixture: {str(e)}'
                            current_app.logger.error(error_msg)
                            db.session.rollback()
                            flash(error_msg, 'danger')
                            error_count += 1
                            continue
                        
                    except ValueError as ve:
                        error_msg = f'Invalid gameweek number in line: {fixture_line}'
                        log_error(ve, error_msg)
                        flash(error_msg, 'danger')
                        error_count += 1
                        continue
                        
                if success_count > 0:
                    db.session.commit()
                    flash(f'Successfully created {success_count} fixtures!', 'success')
                if error_count > 0:
                    flash(f'Failed to create {error_count} fixtures. Check the error messages above.', 'warning')
                    
            except Exception as e:
                db.session.rollback()
                error_msg = f'Error processing fixtures: {str(e)}'
                log_error(e, "processing fixtures")
                flash(error_msg, 'danger')
                
        # Get existing fixtures
        fixtures = Fixture.query.join(Gameweek).filter(
            Gameweek.season_id == current_season.id
        ).order_by(Gameweek.number).all()
            
    except Exception as e:
        error_msg = log_error(e, "unexpected error")
        flash(f'An unexpected error occurred: {error_msg}', 'danger')
        fixtures = []
    
    return render_template('admin/fixtures.html', title='Manage Fixtures',
                         form=form, fixtures=fixtures)
                        
                        # Try to find teams (names should already be normalized in the database)
                        home_team = all_teams.get(home_team_name)
                        away_team = all_teams.get(away_team_name)
                        
                        # Get the gameweek for the current season
                        gameweek = Gameweek.query.filter_by(
                            season_id=current_season.id,
                            number=gameweek_number
                        ).first()
                        
                        if gameweek:
                            if home_team and away_team:
                                # Check if fixture already exists
                                existing_fixture = Fixture.query.filter_by(
                                    gameweek_id=gameweek.id,
                                    home_team_id=home_team.id,
                                    away_team_id=away_team.id
                                ).first()
                                
                                if not existing_fixture:
                                    fixture = Fixture(
                                        gameweek_id=gameweek.id,
                                        home_team_id=home_team.id,
                                        away_team_id=away_team.id,
                                        division_id=form.division_id.data
                                    )
                                    db.session.add(fixture)
                                    success_count += 1
                                else:
                                    error_count += 1
                                    flash(f'Fixture already exists: GW{gameweek_number} - {home_team_name} vs {away_team_name}', 'warning')
                            else:
                                error_count += 1
                                if not home_team:
                                    flash(f'Could not find home team: "{home_team_name}". Check for special characters or typos.', 'danger')
                                if not away_team:
                                    flash(f'Could not find away team: "{away_team_name}". Check for special characters or typos.', 'danger')
                        else:
                            error_count += 1
                            flash(f'Could not find gameweek {gameweek_number} in the current season', 'danger')
                    except ValueError:
                        error_count += 1
                        flash(f'Invalid gameweek number in line: {fixture_line}', 'danger')
                        continue
                else:
                    error_count += 1
                    flash(f'Invalid line format: {fixture_line}', 'danger')
            
            try:
                db.session.commit()
                if success_count > 0:
                    flash(f'Successfully created {success_count} fixtures!', 'success')
                if error_count > 0:
                    flash(f'Failed to create {error_count} fixtures. Check the error messages above.', 'warning')
            except Exception as e:
                db.session.rollback()
                flash(f'Database error: {str(e)}', 'danger')
            return redirect(url_for('admin.manage_fixtures'))
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'danger')
        return redirect(url_for('admin.manage_fixtures'))
    
    # Get existing fixtures
    fixtures = []
    try:
        fixtures = Fixture.query.join(Gameweek).filter(
            Gameweek.season_id == current_season.id
        ).order_by(Gameweek.number).all()
    except Exception as e:
        flash(f'Error loading fixtures: {str(e)}', 'danger')
    
    return render_template('admin/fixtures.html', title='Manage Fixtures',
                         form=form, fixtures=fixtures)

@bp.route('/scores', methods=['GET', 'POST'])
@login_required
@admin_required
def upload_scores():
    form = ScoreUploadForm()
    current_season = Season.query.filter_by(is_current=True).first()
    
    # Populate form choices
    if current_season:
        # Get gameweeks
        gameweeks = Gameweek.query.filter_by(season_id=current_season.id).order_by(Gameweek.number.desc()).all()
        form.gameweek.choices = [(gw.id, f'Gameweek {gw.number}') for gw in gameweeks]
        
        # Get divisions
        divisions = Division.query.filter_by(season_id=current_season.id).all()
        form.division.choices = [(d.id, d.name) for d in divisions]
        
        if form.validate_on_submit():
            gameweek = Gameweek.query.get(form.gameweek.data)
            division = Division.query.get(form.division.data)
            
            # Get existing fixtures for validation
            existing_fixtures = {
                (f.home_team.name, f.away_team.name): f
                for f in Fixture.query.filter_by(
                    gameweek_id=gameweek.id,
                    division_id=division.id
                ).all()
            }
            
            # Parse scores
            scores = []
            errors = []
            score_lines = form.scores_text.data.strip().split('\n')
            
            for line in score_lines:
                parts = [p.strip() for p in line.split('\t') if p.strip()]
                if len(parts) == 4:  # Home Team, Home Score, Away Team, Away Score
                    try:
                        home_team = parts[0]
                        home_score = float(parts[1])
                        away_team = parts[2]
                        away_score = float(parts[3])
                        
                        # Normalize team names
                        home_team = normalize_team_name(home_team)
                        away_team = normalize_team_name(away_team)
                        
                        # Check if this fixture exists
                        fixture = existing_fixtures.get((home_team, away_team))
                        if not fixture:
                            errors.append(f'No fixture found for {home_team} vs {away_team} in Gameweek {gameweek.number}')
                        else:
                            scores.append((fixture, home_score, away_score))
                    except ValueError:
                        errors.append(f'Invalid score format in line: {line}')
                else:
                    errors.append(f'Invalid line format: {line}')
            
            # Validate that all fixtures are accounted for
            for (home_team, away_team), fixture in existing_fixtures.items():
                if not any(s[0] == fixture for s in scores):
                    errors.append(f'Missing score for fixture: {home_team} vs {away_team}')
            
            if errors:
                for error in errors:
                    flash(error, 'danger')
            else:
                # All validation passed, update scores
                for fixture, home_score, away_score in scores:
                    fixture.home_score = home_score
                    fixture.away_score = away_score
                    
                    # Update team points and scores
                    home_team_season = TeamSeason.query.filter_by(
                        team_id=fixture.home_team_id,
                        season_id=current_season.id
                    ).first()
                    away_team_season = TeamSeason.query.filter_by(
                        team_id=fixture.away_team_id,
                        season_id=current_season.id
                    ).first()
                    
                    # Recalculate totals for both teams
                    home_team_season.recalculate_totals()
                    away_team_season.recalculate_totals()
                
                db.session.commit()
                
                # Update Manager of the Month winners
                months = ManagerMonth.query.filter_by(season_id=current_season.id).all()
                for month in months:
                    # Only set winner if all fixtures for the month are complete
                    if month.has_fixtures:
                        standings = month.get_standings()
                        if standings:
                            winner = standings[0]['team']
                            if month.winner_id != winner.id:  # Only update if winner has changed
                                # Create or update the ManagerOfTheMonth record
                                existing_award = ManagerOfTheMonth.query.filter_by(
                                    manager_month_id=month.id
                                ).first()
                                
                                if existing_award:
                                    existing_award.team_id = winner.id
                                    existing_award.total_score = standings[0]['goals_for']
                                else:
                                    award = ManagerOfTheMonth(
                                        manager_month_id=month.id,
                                        team_id=winner.id,
                                        total_score=standings[0]['goals_for']
                                    )
                                    db.session.add(award)
                                
                                month.winner_id = winner.id
                                flash(f'{winner.name} has won {month.name}!', 'success')
                
                db.session.commit()
                
                # Update cup matches if this gameweek has any
                cup_rounds = CupRound.query.filter(
                    (CupRound.first_leg_gameweek_id == form.gameweek.data) |
                    (CupRound.second_leg_gameweek_id == form.gameweek.data)
                ).all()
                
                for round in cup_rounds:
                    for match in round.matches:
                        match.update_scores_from_fixtures()
                
                db.session.commit()
                
                flash('Scores uploaded successfully!', 'success')
                return redirect(url_for('admin.upload_scores'))
    
    # Get recent fixtures for display
    recent_fixtures = []
    if current_season:
        recent_fixtures = Fixture.query.join(Gameweek).filter(
            Gameweek.season_id == current_season.id
        ).order_by(Gameweek.number.desc()).limit(5).all()
    
    return render_template('admin/scores.html',
                         title='Upload Scores',
                         form=form,
                         recent_fixtures=recent_fixtures)

@bp.route('/cups', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_cups():
    form = CupCompetitionForm()
    current_season = Season.query.filter_by(is_current=True).first()
    
    if not current_season:
        flash('No current season found. Please create a season first.', 'warning')
        return redirect(url_for('admin.manage_seasons'))
    
    if form.validate_on_submit():
        try:
            # Validate group settings
            if form.has_groups.data:
                if not form.num_groups.data or form.num_groups.data < 1:
                    flash('Number of groups must be at least 1', 'danger')
                    return render_template('admin/cups.html', title='Manage Cups',
                                        form=form, cups=CupCompetition.query.filter_by(season_id=current_season.id).all())
                if not form.teams_per_group.data or form.teams_per_group.data < 2:
                    flash('Teams per group must be at least 2', 'danger')
                    return render_template('admin/cups.html', title='Manage Cups',
                                        form=form, cups=CupCompetition.query.filter_by(season_id=current_season.id).all())
            
            cup = CupCompetition(
                name=form.name.data, 
                season_id=current_season.id,
                has_groups=form.has_groups.data,
                num_groups=form.num_groups.data if form.has_groups.data else 0,
                teams_per_group=form.teams_per_group.data if form.has_groups.data else 0
            )
            db.session.add(cup)
            db.session.commit()
            
            # Create initial groups if using group format
            if cup.has_groups:
                try:
                    cup.create_initial_groups()
                except Exception as e:
                    db.session.delete(cup)
                    db.session.commit()
                    flash(f'Error creating groups: {str(e)}', 'danger')
                    return render_template('admin/cups.html', title='Manage Cups',
                                        form=form, cups=CupCompetition.query.filter_by(season_id=current_season.id).all())
            
            flash(f'Cup competition {cup.name} has been created!', 'success')
            return redirect(url_for('admin.manage_cups'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating cup competition: {str(e)}', 'danger')
    
    cups = CupCompetition.query.filter_by(season_id=current_season.id).all()
    return render_template('admin/cups.html', title='Manage Cups',
                         form=form, cups=cups)

@bp.route('/cup/<int:cup_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_cup(cup_id):
    cup = CupCompetition.query.get_or_404(cup_id)
    
    # Delete group-related data if it's a group-based cup
    if cup.has_groups:
        for group in cup.groups:
            # Delete group matches
            CupGroupMatch.query.filter_by(group_id=group.id).delete()
            # Delete group team assignments
            CupGroupTeam.query.filter_by(group_id=group.id).delete()
        # Delete groups
        CupGroup.query.filter_by(competition_id=cup.id).delete()
    
    # Delete all associated matches first
    for round in cup.rounds:
        CupMatch.query.filter_by(round_id=round.id).delete()
    
    # Delete all rounds
    CupRound.query.filter_by(competition_id=cup.id).delete()
    
    # Delete the cup competition
    db.session.delete(cup)
    db.session.commit()
    
    flash(f'Cup competition {cup.name} has been deleted!', 'success')
    return redirect(url_for('admin.manage_cups'))

@bp.route('/cup/<int:cup_id>/rounds', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_cup_rounds(cup_id):
    cup = CupCompetition.query.get_or_404(cup_id)
    form = CupRoundForm()
    current_season = Season.query.filter_by(is_current=True).first()
    
    if current_season:
        gameweeks = Gameweek.query.filter_by(season_id=current_season.id).all()
        form.first_leg_gameweek_id.choices = [(g.id, f'Gameweek {g.number}') for g in gameweeks]
        form.second_leg_gameweek_id.choices = [(g.id, f'Gameweek {g.number}') for g in gameweeks]
        
        if form.validate_on_submit():
            round = CupRound(
                name=form.name.data,
                competition_id=cup.id,
                order=form.order.data,
                num_matches=form.num_matches.data,
                first_leg_gameweek_id=form.first_leg_gameweek_id.data,
                second_leg_gameweek_id=form.second_leg_gameweek_id.data
            )
            db.session.add(round)
            db.session.flush()
            
            # Create empty matches for this round
            for _ in range(form.num_matches.data):
                match = CupMatch(round_id=round.id)
                db.session.add(match)
            
            db.session.commit()
            flash(f'Round {round.name} has been created with {round.num_matches} empty matches!', 'success')
            return redirect(url_for('admin.manage_cup_rounds', cup_id=cup.id))
    
    rounds = CupRound.query.filter_by(competition_id=cup.id).order_by(CupRound.order).all()
    return render_template('admin/cup_rounds.html', title=f'Manage {cup.name} Rounds',
                         form=form, cup=cup, rounds=rounds)

@bp.route('/cup/round/<int:round_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_cup_round(round_id):
    cup_round = CupRound.query.get_or_404(round_id)
    cup_id    = cup_round.competition_id

    # Build the same form you use for create
    form = CupRoundForm(obj=cup_round)
    current_season = Season.query.filter_by(is_current=True).first()
    if not current_season:
        flash('No active season.', 'danger')
        return redirect(url_for('admin.manage_cup_rounds', cup_id=cup_id))

    # Populate gameweek choices
    gameweeks = Gameweek.query.filter_by(season_id=current_season.id).all()
    form.first_leg_gameweek_id.choices  = [(g.id, f'GW {g.number}') for g in gameweeks]
    form.second_leg_gameweek_id.choices = [(g.id, f'GW {g.number}') for g in gameweeks]

    if form.validate_on_submit():
        # copy over the edited fields
        cup_round.name                  = form.name.data
        cup_round.order                 = form.order.data
        cup_round.num_matches           = form.num_matches.data
        cup_round.first_leg_gameweek_id = form.first_leg_gameweek_id.data
        cup_round.second_leg_gameweek_id= form.second_leg_gameweek_id.data

        db.session.commit()
        flash(f'Round "{cup_round.name}" updated!', 'success')
        return redirect(url_for('admin.manage_cup_rounds', cup_id=cup_id))

    return render_template(
        'admin/edit_cup_round.html',
        title=f'Edit {cup_round.name}',
        form=form,
        cup_id=cup_id
    )

@bp.route('/cup/round/<int:round_id>/matches', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_cup_matches(round_id):
    cup_round = CupRound.query.get_or_404(round_id)
    teams = []

    # ── AUTO-SYNC: clear old scores and re-pull from fixtures ───────────────
    for match in cup_round.matches:
        # wipe any previously stored leg scores
        match.first_leg_home_score  = None
        match.first_leg_away_score  = None
        match.second_leg_home_score = None
        match.second_leg_away_score = None

        # now re-populate from Fixture data
        match.update_scores_from_fixtures()

    db.session.commit()
    # ────────────────────────────────────────────────────────────────────────

    form = CupMatchForm()
    current_season = Season.query.filter_by(is_current=True).first()
    if current_season:
        # Always list every team alphabetically for manual pairing
        teams = Team.query \
                    .join(TeamSeason) \
                    .filter(TeamSeason.season_id == current_season.id) \
                    .all()
        teams = sorted(teams, key=lambda t: t.name)

    form.home_team_id.choices = [(t.id, t.name) for t in teams]
    form.away_team_id.choices = [(t.id, t.name) for t in teams]

    # New logic: handle POST for update or create, before fetching matches
    if request.method == 'POST':
        # Update existing match if match_id is provided
        match_id = form.match_id.data or request.form.get('match_id')
        if match_id:
            match = CupMatch.query.get(int(match_id))
            match.home_team_id = form.home_team_id.data
            match.away_team_id = form.away_team_id.data
            db.session.commit()
            flash(f'Match {match.id} updated!', 'success')
        else:
            # creating a new match
            new_match = CupMatch(
                round_id=cup_round.id,
                home_team_id=form.home_team_id.data,
                away_team_id=form.away_team_id.data
            )
            db.session.add(new_match)
            db.session.commit()
            flash('Match added!', 'success')
        return redirect(url_for('admin.manage_cup_matches', round_id=round_id))

    matches = cup_round.matches
    return render_template(
        'admin/cup_matches.html',
        title=f'Matches for {cup_round.name}',
        form=form,
        matches=matches,
        teams=teams
    )

@bp.route('/cup/<int:cup_id>/groups', methods=['GET'])
@login_required
@admin_required
def manage_cup_groups(cup_id):
    cup = CupCompetition.query.get_or_404(cup_id)
    if not cup.has_groups:
        flash('This cup competition does not use group format.', 'warning')
        return redirect(url_for('admin.manage_cups'))
    
    groups = CupGroup.query.filter_by(competition_id=cup_id).order_by(CupGroup.order).all()
    
    # Get qualification info if group stage is complete
    group_stage_complete = cup.group_stage_complete
    direct_qualifiers = []
    playoff_teams = []
    
    if group_stage_complete:
        direct_qualifiers = cup.get_direct_qualifiers()
        playoff_teams = cup.get_playoff_teams()
    
    return render_template('admin/cup_groups.html', title=f'{cup.name} - Groups',
                         cup=cup, groups=groups, 
                         group_stage_complete=group_stage_complete,
                         direct_qualifiers=direct_qualifiers,
                         playoff_teams=playoff_teams)

@bp.route('/cup/group/<int:group_id>/teams', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_group_teams(group_id):
    group = CupGroup.query.get_or_404(group_id)
    form = CupGroupTeamForm()
    
    current_season = Season.query.filter_by(is_current=True).first()
    if current_season:
        # Get all teams not already in this group
        assigned_team_ids = [gt.team_id for gt in group.teams]
        available_teams = Team.query \
            .join(TeamSeason) \
            .filter(TeamSeason.season_id == current_season.id) \
            .filter(~Team.id.in_(assigned_team_ids)) \
            .all()
        
        form.team_id.choices = [(t.id, t.name) for t in available_teams]
        
        if form.validate_on_submit() and len(group.teams) < group.competition.teams_per_group:
            group_team = CupGroupTeam(
                group_id=group.id,
                team_id=form.team_id.data
            )
            db.session.add(group_team)
            db.session.commit()
            flash('Team added to group!', 'success')
            return redirect(url_for('admin.manage_group_teams', group_id=group_id))
    
    return render_template('admin/group_teams.html', title=f'{group.name} - Teams',
                         group=group, form=form)

@bp.route('/cup/group/<int:group_id>/teams/<int:team_id>/remove', methods=['POST'])
@login_required
@admin_required
def remove_group_team(group_id, team_id):
    group_team = CupGroupTeam.query.filter_by(group_id=group_id, team_id=team_id).first_or_404()
    db.session.delete(group_team)
    db.session.commit()
    flash('Team removed from group!', 'success')
    return redirect(url_for('admin.manage_group_teams', group_id=group_id))

@bp.route('/cup/group/<int:group_id>/matches', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_group_matches(group_id):
    group = CupGroup.query.get_or_404(group_id)
    form = CupGroupMatchForm()
    
    current_season = Season.query.filter_by(is_current=True).first()
    if current_season:
        # Get teams in this group
        group_teams = [gt.team for gt in group.teams]
        form.home_team_id.choices = [(t.id, t.name) for t in group_teams]
        form.away_team_id.choices = [(t.id, t.name) for t in group_teams]
        
        # Get gameweeks
        gameweeks = Gameweek.query.filter_by(season_id=current_season.id).all()
        form.gameweek_id.choices = [(0, 'No Gameweek')] + [(g.id, f'Gameweek {g.number}') for g in gameweeks]
        
        if form.validate_on_submit():
            # Check if match already exists
            existing = CupGroupMatch.query.filter_by(
                group_id=group_id,
                home_team_id=form.home_team_id.data,
                away_team_id=form.away_team_id.data
            ).first()
            
            if not existing and form.home_team_id.data != form.away_team_id.data:
                match = CupGroupMatch(
                    group_id=group_id,
                    home_team_id=form.home_team_id.data,
                    away_team_id=form.away_team_id.data,
                    gameweek_id=form.gameweek_id.data if form.gameweek_id.data != 0 else None
                )
                db.session.add(match)
                db.session.commit()
                flash('Match created!', 'success')
            else:
                flash('Match already exists or teams are the same!', 'error')
            
            return redirect(url_for('admin.manage_group_matches', group_id=group_id))
    
    # Update scores from fixtures
    for match in group.matches:
        match.update_scores_from_fixtures()
    db.session.commit()
    
    return render_template('admin/group_matches.html', title=f'{group.name} - Matches',
                         group=group, form=form)

@bp.route('/cup/group/match/<int:match_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_group_match(match_id):
    match = CupGroupMatch.query.get_or_404(match_id)
    group_id = match.group_id
    db.session.delete(match)
    db.session.commit()
    flash('Match deleted!', 'success')
    return redirect(url_for('admin.manage_group_matches', group_id=group_id))

@bp.route('/cup/group/match/<int:match_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_group_match(match_id):
    match = CupGroupMatch.query.get_or_404(match_id)
    form = EditCupGroupMatchForm()
    
    current_season = Season.query.filter_by(is_current=True).first()
    if current_season:
        gameweeks = Gameweek.query.filter_by(season_id=current_season.id).all()
        form.gameweek_id.choices = [(0, 'No Gameweek')] + [(g.id, f'Gameweek {g.number}') for g in gameweeks]
        
        if form.validate_on_submit():
            match.gameweek_id = form.gameweek_id.data if form.gameweek_id.data != 0 else None
            db.session.commit()
            flash('Match updated!', 'success')
            return redirect(url_for('admin.manage_group_matches', group_id=match.group_id))
        
        # Pre-populate form
        if request.method == 'GET':
            form.gameweek_id.data = match.gameweek_id if match.gameweek_id else 0
    
    return render_template('admin/edit_group_match.html', title='Edit Match',
                         form=form, match=match)

@bp.route('/cup/group/<int:group_id>/generate-matches', methods=['POST'])
@login_required
@admin_required
def generate_group_matches(group_id):
    group = CupGroup.query.get_or_404(group_id)
    
    # Get all teams in the group
    teams = [gt.team for gt in group.teams]
    
    if len(teams) < 2:
        flash('Need at least 2 teams to generate matches!', 'error')
        return redirect(url_for('admin.manage_group_matches', group_id=group_id))
    
    # Generate all possible combinations (round robin)
    matches_created = 0
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            home_team = teams[i]
            away_team = teams[j]
            
            # Check if match already exists
            existing = CupGroupMatch.query.filter_by(
                group_id=group_id,
                home_team_id=home_team.id,
                away_team_id=away_team.id
            ).first()
            
            if not existing:
                # Create the match (without a gameweek - admin can set later)
                match = CupGroupMatch(
                    group_id=group_id,
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                    gameweek_id=None  # To be set by admin
                )
                db.session.add(match)
                matches_created += 1
    
    db.session.commit()
    flash(f'{matches_created} matches created! You can now assign gameweeks to each match.', 'success')
    return redirect(url_for('admin.manage_group_matches', group_id=group_id))

@bp.route('/manager-month', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_manager_month():
    form = ManagerMonthForm()
    current_season = Season.query.filter_by(is_current=True).first()
    if current_season:
        gameweeks = Gameweek.query.filter_by(season_id=current_season.id).all()
        form.start_gameweek_id.choices = [(g.id, f'Gameweek {g.number}') for g in gameweeks]
        form.end_gameweek_id.choices = [(g.id, f'Gameweek {g.number}') for g in gameweeks]
        
        if form.validate_on_submit():
            month = ManagerMonth(
                name=form.name.data,
                season_id=current_season.id,
                start_gameweek_id=form.start_gameweek_id.data,
                end_gameweek_id=form.end_gameweek_id.data
            )
            db.session.add(month)
            db.session.flush()  # Get the ID without committing
            
            # Calculate standings and set winner
            if month.has_fixtures:
                standings = month.get_standings()
                if standings:
                    winner = standings[0]['team']
                    month.winner_id = winner.id
                    
                    # Create the ManagerOfTheMonth record
                    award = ManagerOfTheMonth(
                        manager_month_id=month.id,
                        team_id=winner.id,
                        total_score=standings[0]['goals_for']
                    )
                    db.session.add(award)
                    
                    flash(f'{winner.name} has won {month.name}!', 'success')
                else:
                    flash('No teams found with fixtures in this period.', 'warning')
            else:
                flash('No fixtures with scores found in this period.', 'warning')
            
            db.session.commit()
            flash(f'Manager Month {month.name} has been created!', 'success')
            return redirect(url_for('admin.manage_manager_month'))
    
    months = []
    if current_season:
        months = ManagerMonth.query.filter_by(season_id=current_season.id).all()
    
    return render_template('admin/manager_month.html', title='Manage Manager of the Month',
                         form=form, months=months)

@bp.route('/seasons', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_seasons():
    form = SeasonForm()
    if form.validate_on_submit():
        if form.is_current.data:
            # Set all other seasons to not current
            Season.query.filter_by(is_current=True).update({'is_current': False})
        
        season = Season(
            name=form.name.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            is_current=form.is_current.data
        )
        db.session.add(season)
        db.session.commit()
        flash(f'Season {season.name} has been created!', 'success')
        return redirect(url_for('admin.manage_seasons'))
    
    seasons = Season.query.order_by(Season.start_date.desc()).all()
    return render_template('admin/seasons.html', title='Manage Seasons',
                         form=form, seasons=seasons)

@bp.route('/edit-season/<int:season_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_season(season_id):
    season = Season.query.get_or_404(season_id)
    form = EditSeasonForm()
    
    if form.validate_on_submit():
        if form.is_current.data and not season.is_current:
            # If making this season current, set all other seasons to not current
            Season.query.filter_by(is_current=True).update({'is_current': False})
        
        season.name = form.name.data
        season.start_date = form.start_date.data
        season.end_date = form.end_date.data
        season.is_current = form.is_current.data
        
        db.session.commit()
        flash(f'Season {season.name} has been updated!', 'success')
        return redirect(url_for('admin.manage_seasons'))
    
    # Pre-populate form with current season data
    if request.method == 'GET':
        form.name.data = season.name
        form.start_date.data = season.start_date
        form.end_date.data = season.end_date
        form.is_current.data = season.is_current
    
    return render_template('admin/edit_season.html', title='Edit Season',
                         form=form, season=season)

@bp.route('/api/teams/<int:division_id>')
@login_required
@admin_required
def get_teams(division_id):
    current_season = Season.query.filter_by(is_current=True).first()
    if not current_season:
        return jsonify([])
    
    teams = Team.query.join(TeamSeason).filter(
        TeamSeason.division_id == division_id,
        TeamSeason.season_id == current_season.id
    ).all()
    
    return jsonify([{'id': team.id, 'name': team.name} for team in teams]) 

@bp.route('/admin/rules', methods=['GET','POST'])
@login_required
@admin_required
def edit_rules():
    rule = Rule.query.first()
    form = RulesForm()
    if form.validate_on_submit():
        if not rule:
            rule = Rule(content=form.content.data)
            db.session.add(rule)
        else:
            rule.content = form.content.data
        db.session.commit()
        flash('Rules updated', 'success')
        return redirect(url_for('admin.edit_rules'))
    # on GET, pre-fill the editor
    if rule and request.method == 'GET':
        form.content.data = rule.content
    return render_template('admin/edit_rules.html', form=form)

@bp.route('/end-season', methods=['GET', 'POST'])
@login_required
@admin_required
def end_season():
    current_season = Season.query.filter_by(is_current=True).first()
    if not current_season:
        flash('No active season found!', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    form = EndSeasonForm()
    if form.validate_on_submit():
        # End current season
        current_season.is_current = False
        
        # Create new season
        new_season = Season(
            name='2025/26',
            start_date=datetime(2025, 8, 1).date(),
            end_date=datetime(2026, 5, 31).date(),
            is_current=True
        )
        db.session.add(new_season)
        db.session.flush()  # Get the ID
        
        # Create divisions for new season
        premier_league = Division(name='Premier League', season_id=new_season.id)
        championship = Division(name='Championship', season_id=new_season.id)
        db.session.add(premier_league)
        db.session.add(championship)
        db.session.flush()
        
        # Handle promotions and relegations
        current_divisions = Division.query.filter_by(season_id=current_season.id).all()
        
        for division in current_divisions:
            # Get final standings for current season
            team_seasons = TeamSeason.query.filter_by(
                season_id=current_season.id, 
                division_id=division.id
            ).order_by(TeamSeason.points.desc(), TeamSeason.total_score.desc()).all()
            
            for i, team_season in enumerate(team_seasons):
                team_season.position = i + 1
                
                # Determine division for next season
                if division.name == 'Premier League':
                    if i < 4:  # Top 4 stay in Premier League
                        new_division = premier_league
                    else:  # Bottom 2 relegated to Championship
                        new_division = championship
                elif division.name == 'Championship':
                    if i < 2:  # Top 2 promoted to Premier League
                        new_division = premier_league
                    else:  # Rest stay in Championship
                        new_division = championship
                else:
                    # Default to Championship for other divisions
                    new_division = championship
                
                # Create new TeamSeason for new season
                new_team_season = TeamSeason(
                    team_id=team_season.team_id,
                    season_id=new_season.id,
                    division_id=new_division.id,
                    points=0,
                    total_score=0.0
                )
                db.session.add(new_team_season)
        
        # Delete any existing gameweeks for the new season
        Gameweek.query.filter_by(season_id=new_season.id).delete()
        
        # Reset gameweek numbering for new season
        # Create 38 gameweeks for new season
        for week in range(1, 39):
            gameweek = Gameweek(
                number=week,
                season_id=new_season.id,
                deadline=datetime(2025, 8, 1),  # Default deadline
                is_current=week == 1
            )
            db.session.add(gameweek)
            
        # Flush to ensure all gameweeks are created properly
        db.session.flush()
        
        db.session.commit()
        flash(f'Season {current_season.name} has been ended and {new_season.name} has been created!', 'success')
        return redirect(url_for('admin.dashboard'))
    
    return render_template('admin/end_season.html', form=form, season=current_season)