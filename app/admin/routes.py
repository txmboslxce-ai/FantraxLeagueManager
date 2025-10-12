from flask import render_template, flash, redirect, url_for, current_app, request
from flask_login import login_required
from app import db
from app.admin import bp
from app.admin.forms import (BulkFixtureForm, DivisionForm, TeamForm, 
                           EndSeasonForm, TitleForm, EditTeamForm, ScoreUploadForm)
from app.admin.decorators import admin_required
from app.models import Season, Division, Gameweek, Team, Fixture, TeamSeason, Title, ManagerOfTheMonth
from app.utils import normalize_team_name
from sqlalchemy import text, or_
import traceback
import re

@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    current_season = Season.query.filter_by(is_current=True).first()
    return render_template('admin/dashboard.html', season=current_season)

@bp.route('/seasons')
@login_required
@admin_required
def manage_seasons():
    seasons = Season.query.order_by(Season.start_date.desc()).all()
    return render_template('admin/seasons.html', seasons=seasons)

@bp.route('/divisions', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_divisions():
    current_season = Season.query.filter_by(is_current=True).first()
    if not current_season:
        flash('No current season found. Please create a season first.', 'warning')
        return redirect(url_for('admin.manage_seasons'))
        
    form = DivisionForm()
    divisions = Division.query.filter_by(season_id=current_season.id).all()
    return render_template('admin/divisions.html', divisions=divisions, season=current_season, form=form)

@bp.route('/teams', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_teams():
    current_season = Season.query.filter_by(is_current=True).first()
    if not current_season:
        flash('No current season found. Please create a season first.', 'warning')
        return redirect(url_for('admin.manage_seasons'))
        
    form = TeamForm()
    form.division_id.choices = [(d.id, d.name) for d in Division.query.filter_by(season_id=current_season.id).all()]
    
    if form.validate_on_submit():
        try:
            # Check if team name already exists
            existing_team = Team.query.filter_by(name=form.name.data).first()
            if existing_team:
                flash(f'A team with name "{form.name.data}" already exists.', 'danger')
                return redirect(url_for('admin.manage_teams'))
                
            # Get next available ID
            result = db.session.execute(text("SELECT COALESCE(MAX(id), 0) + 1 FROM team"))
            next_id = result.scalar()
            
            team = Team(
                id=next_id,
                name=form.name.data,
                manager_name=form.manager_name.data
            )
            db.session.add(team)
            db.session.flush()  # Get the team ID
            
            # Create TeamSeason relationship
            # Get next available ID for team_season
            result = db.session.execute(text("SELECT COALESCE(MAX(id), 0) + 1 FROM team_season"))
            next_team_season_id = result.scalar()
            
            team_season = TeamSeason(
                id=next_team_season_id,
                team_id=team.id,
                season_id=current_season.id,
                division_id=form.division_id.data,
                points=0,
                total_score=0,
                position=0  # Initialize with 0 instead of None
            )
            db.session.add(team_season)
            db.session.commit()
            
            flash(f'Team {team.name} created successfully.', 'success')
            return redirect(url_for('admin.manage_teams'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating team: {str(e)}', 'danger')
    
    teams = Team.query.all()
    return render_template('admin/teams.html', teams=teams, form=form)

@bp.route('/teams/<int:team_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_team(team_id):
    team = Team.query.get_or_404(team_id)
    try:
        # First delete all team_season entries
        TeamSeason.query.filter_by(team_id=team_id).delete()
        
        # Then delete any titles
        Title.query.filter_by(team_id=team_id).delete()
        
        # Delete any manager of the month awards
        ManagerOfTheMonth.query.filter_by(team_id=team_id).delete()
        
        # Delete any fixtures where this team is involved
        Fixture.query.filter(
            or_(
                Fixture.home_team_id == team_id,
                Fixture.away_team_id == team_id
            )
        ).delete()
        
        # Finally delete the team
        db.session.delete(team)
        db.session.commit()
        flash(f'Team {team.name} and all related data deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting team: {str(e)}')
        current_app.logger.error(traceback.format_exc())
        flash(f'Error deleting team: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_teams'))

@bp.route('/teams/<int:team_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_team(team_id):
    team = Team.query.get_or_404(team_id)
    form = EditTeamForm()
    
    if form.validate_on_submit():
        try:
            team.name = form.name.data
            team.manager_name = form.manager_name.data
            db.session.commit()
            flash('Team updated successfully.', 'success')
            return redirect(url_for('admin.manage_teams'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating team: {str(e)}', 'danger')
            
    # Pre-populate form with current values
    if request.method == 'GET':
        form.name.data = team.name
        form.manager_name.data = team.manager_name
        
    return render_template('admin/edit_team.html', form=form, team=team)

@bp.route('/teams/<int:team_id>/titles', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_team_titles(team_id):
    team = Team.query.get_or_404(team_id)
    
    form = TitleForm()
    # Set up season choices
    form.season_id.choices = [(s.id, s.name) for s in Season.query.order_by(Season.start_date.desc()).all()]
    # Set up division choices
    form.division_id.choices = [(d.id, d.name) for d in Division.query.all()]
    # Set the team_id to the current team and disable the field as it's predetermined
    form.team_id.data = team_id
    form.team_id.render_kw = {'disabled': 'disabled'}
    
    # Get all existing titles for this team
    titles = Title.query.filter_by(team_id=team_id).order_by(Title.season_id.desc()).all()
    
    if form.validate_on_submit():
        try:
            # Check if title already exists
            existing_title = Title.query.filter_by(
                team_id=team_id,
                season_id=form.season_id.data,
                type=form.type.data,
                division_id=form.division_id.data if form.type.data == 'league' else None,
                is_runner_up=form.is_runner_up.data
            ).first()
            
            if not existing_title:
                title = Title(
                    team_id=team_id,
                    season_id=form.season_id.data,
                    type=form.type.data,
                    division_id=form.division_id.data if form.type.data == 'league' else None,
                    is_runner_up=form.is_runner_up.data
                )
                db.session.add(title)
                db.session.commit()
                flash('Title added successfully.', 'success')
            else:
                flash('This title already exists for this team.', 'warning')
                
        except Exception as e:
            flash(f'Error adding title: {str(e)}', 'danger')
            db.session.rollback()
            
    return render_template('admin/team_titles.html', 
                         team=team,
                         form=form,
                         titles=titles)
                         
@bp.route('/titles/<int:title_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_title(title_id):
    title = Title.query.get_or_404(title_id)
    team_id = title.team_id
    try:
        db.session.delete(title)
        db.session.commit()
        flash('Title deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting title: {str(e)}', 'danger')
        db.session.rollback()
        
    return redirect(url_for('admin.manage_team_titles', team_id=team_id))

def award_league_titles(season_id):
    """Award league titles for all divisions in a season"""
    divisions = Division.query.filter_by(season_id=season_id).all()
    
    for division in divisions:
        # Get the champion (team in position 1)
        champion = TeamSeason.query.filter_by(
            division_id=division.id,
            season_id=season_id,
            position=1
        ).first()
        
        if champion:
            # Check if title already exists
            existing_title = Title.query.filter_by(
                team_id=champion.team_id,
                season_id=season_id,
                type='league',
                division_id=division.id,
                is_runner_up=False
            ).first()
            
            if not existing_title:
                # Create the title
                title = Title(
                    team_id=champion.team_id,
                    season_id=season_id,
                    type='league',
                    division_id=division.id,
                    is_runner_up=False
                )
                db.session.add(title)
                
        # Get the runner-up (position 2)
        runner_up = TeamSeason.query.filter_by(
            division_id=division.id,
            season_id=season_id,
            position=2
        ).first()
        
        if runner_up:
            # Check if runner-up title already exists
            existing_title = Title.query.filter_by(
                team_id=runner_up.team_id,
                season_id=season_id,
                type='league',
                division_id=division.id,
                is_runner_up=True
            ).first()
            
            if not existing_title:
                # Create the runner-up title
                title = Title(
                    team_id=runner_up.team_id,
                    season_id=season_id,
                    type='league',
                    division_id=division.id,
                    is_runner_up=True
                )
                db.session.add(title)
    
    db.session.commit()

@bp.route('/end-season', methods=['GET', 'POST'])
@login_required
@admin_required
def end_season():
    current_season = Season.query.filter_by(is_current=True).first()
    if not current_season:
        flash('No current season found.', 'warning')
        return redirect(url_for('admin.manage_seasons'))
        
    form = EndSeasonForm()
    
    if form.validate_on_submit() and form.confirm.data:
        try:
            # Award league titles before ending the season
            award_league_titles(current_season.id)
            
            # Proceed with season end logic...
            # [Your existing season end code here]
            
            flash('Season ended successfully and titles awarded.', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            current_app.logger.error(f"Error ending season: {str(e)}")
            flash('Error ending season. Please check the logs.', 'danger')
            db.session.rollback()
            
    return render_template('admin/end_season.html', season=current_season, form=form)

@bp.route('/upload-scores', methods=['GET', 'POST'])
@login_required
@admin_required
def upload_scores():
    current_season = Season.query.filter_by(is_current=True).first()
    if not current_season:
        flash('No current season found. Please create a season first.', 'warning')
        return redirect(url_for('admin.manage_seasons'))
        
    form = ScoreUploadForm()
    
    # Set up form choices
    form.gameweek.choices = [(gw.id, f'Gameweek {gw.number}') 
                            for gw in Gameweek.query.filter_by(season_id=current_season.id)
                            .order_by(Gameweek.number).all()]
                            
    form.division.choices = [(d.id, d.name) 
                            for d in Division.query.filter_by(season_id=current_season.id).all()]
    
    if form.validate_on_submit():
        try:
            print("\nDEBUG INFO:")
            print(f"Raw form data: {form.scores_text.data}")
            print("\nForm validation:")
            print(f"Gameweek ID: {form.gameweek.data}")
            print(f"Division ID: {form.division.data}")
            
            # Process scores upload - first split into lines
            scores = [line for line in form.scores_text.data.strip().splitlines() if line.strip()]
            print(f"\nProcessing {len(scores)} lines:")
            for i, line in enumerate(scores, 1):
                print(f"\nLine {i}: '{line}'")
            
            success_count = 0
            error_count = 0
            
            for score_line in scores:
                if not score_line.strip():
                    continue
                    
                # Split on single space, but intelligently to handle "name score name score" format
                all_parts = score_line.strip().split()
                if len(all_parts) < 4:  # Need at least 4 parts
                    flash(f'Invalid line format (not enough parts): {score_line}', 'danger')
                    error_count += 1
                    continue
                
                # Find the scores (they should be numeric)
                scores_indices = []
                for i, part in enumerate(all_parts):
                    # Remove any trailing trophy emoji from score
                    clean_part = part.split('🏆')[0] if '🏆' in part else part
                    try:
                        float(clean_part)
                        scores_indices.append(i)
                    except ValueError:
                        continue
                
                if len(scores_indices) != 2:
                    flash(f'Could not identify exactly two scores in line: {score_line}', 'danger')
                    error_count += 1
                    continue
                
                # First score position determines team name boundaries
                first_score_pos = scores_indices[0]
                second_score_pos = scores_indices[1]
                
                # Home team name is everything before first score
                home_team_name = ' '.join(all_parts[:first_score_pos])
                # Away team name is everything between scores
                away_team_name = ' '.join(all_parts[first_score_pos + 1:second_score_pos])
                
                # Get the scores (clean any trophy emoji)
                home_score = all_parts[first_score_pos].split('🏆')[0]
                away_score = all_parts[second_score_pos].split('🏆')[0]
                
                print(f"\nParsed line:")
                print(f"Home team: '{home_team_name}'")
                print(f"Home score: {home_score}")
                print(f"Away team: '{away_team_name}'")
                print(f"Away score: {away_score}")
                    
                # Variables already set in the parsing code above
                
                # Get all fixtures for this gameweek and division first
                fixtures = Fixture.query.filter_by(
                    gameweek_id=form.gameweek.data,
                    division_id=form.division.data
                ).all()
                
                print(f"\nLooking for: {home_team_name} vs {away_team_name}")
                print(f"Gameweek ID: {form.gameweek.data}, Division ID: {form.division.data}")
                print(f"Found {len(fixtures)} fixtures for this gameweek/division")
                
                # Get all teams to create a name lookup
                all_teams = {team.id: team for team in Team.query.all()}
                print("\nAll teams in database:")
                for team_id, team in all_teams.items():
                    print(f"ID: {team_id}, Name: {team.name}")
                
                # Find the matching fixture
                fixture = None
                for f in fixtures:
                    home_team = all_teams.get(f.home_team_id)
                    away_team = all_teams.get(f.away_team_id)
                    
                    # Print debug info for each fixture comparison
                    print(f"\nComparing fixture:")
                    print(f"Looking for: '{home_team_name}' vs '{away_team_name}'")
                    if home_team and away_team:
                        print(f"Checking against: '{home_team.name}' vs '{away_team.name}'")
                        print(f"Exact match? Home: {home_team.name == home_team_name}, Away: {away_team.name == away_team_name}")
                    
                    if (home_team and away_team and 
                        home_team.name.strip() == home_team_name.strip() and 
                        away_team.name.strip() == away_team_name.strip()):
                        fixture = f
                        print("MATCH FOUND!")
                        break
                
                if not fixture:
                    flash(f'Could not find fixture for: {home_team_name} vs {away_team_name} in gameweek {form.gameweek.data}', 'danger')
                    error_count += 1
                    continue
                
                # We already have home_team and away_team from the loop above
                
                if not home_team or not away_team:
                    if not home_team:
                        flash(f'Could not find home team: {home_team_name}', 'danger')
                    if not away_team:
                        flash(f'Could not find away team: {away_team_name}', 'danger')
                    error_count += 1
                    continue
                
                try:
                    # Convert scores to float since they can be decimals
                    home_score = float(home_score)
                    away_score = float(away_score)
                except ValueError:
                    flash(f'Invalid score format in line: {score_line}', 'danger')
                    error_count += 1
                    continue
                
                # Update the fixture with scores
                fixture.home_score = home_score
                fixture.away_score = away_score
                fixture.played = True
                
                success_count += 1
            
            if success_count > 0:
                db.session.commit()
                flash(f'Successfully updated {success_count} scores.', 'success')
            
            if error_count > 0:
                flash(f'Failed to update {error_count} scores. Check the error messages above.', 'warning')
                
        except Exception as e:
            db.session.rollback()
            flash(f'Error uploading scores: {str(e)}', 'danger')
    
    return render_template('admin/scores.html', season=current_season, form=form)

@bp.route('/cups')
@login_required
@admin_required
def manage_cups():
    current_season = Season.query.filter_by(is_current=True).first()
    if not current_season:
        flash('No current season found. Please create a season first.', 'warning')
        return redirect(url_for('admin.manage_seasons'))
    return render_template('admin/cups.html', season=current_season)

@bp.route('/manager-month')
@login_required
@admin_required
def manage_manager_month():
    current_season = Season.query.filter_by(is_current=True).first()
    if not current_season:
        flash('No current season found. Please create a season first.', 'warning')
        return redirect(url_for('admin.manage_seasons'))
    return render_template('admin/manager_month.html', season=current_season)

@bp.route('/rules')
@login_required
@admin_required
def edit_rules():
    return render_template('admin/edit_rules.html')

@bp.route('/manage_fixtures', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_fixtures():
    def log_error(e, context=""):
        error_msg = f'Error in manage_fixtures {context}: {str(e)}'
        current_app.logger.error(error_msg)
        if current_app.debug:
            current_app.logger.error(traceback.format_exc())
        return error_msg
    
    form = BulkFixtureForm()
    fixtures = []
    success_count = 0
    error_count = 0

    # Get current season
    current_season = Season.query.filter_by(is_current=True).first()
    if not current_season:
        flash("No current season found. Please create a season first.", 'warning')
        return redirect(url_for('admin.manage_seasons'))

    # Get divisions for current season
    divisions = Division.query.filter_by(season_id=current_season.id).all()
    if not divisions:
        flash("No divisions found for the current season. Please create a division first.", 'warning')
        return redirect(url_for('admin.manage_divisions'))
        
    # Set up division choices before form validation
    form.division_id.choices = [(d.id, d.name) for d in divisions]

    if not form.validate_on_submit():
        return render_template('admin/fixtures.html', form=form, fixtures=fixtures)
    
    # Check division selection
    if not form.division_id.data:
        flash('Please select a division', 'danger')
        return redirect(url_for('admin.manage_fixtures'))
            
    # Get all gameweeks for current season
    all_gameweeks = Gameweek.query.filter_by(season_id=current_season.id).all()
    gameweeks = {gw.number: gw for gw in all_gameweeks}
    
    if not gameweeks:
        flash("No gameweeks found for the current season.", 'danger')
        return redirect(url_for('admin.manage_fixtures'))
            
    # Get all teams
    all_teams = {normalize_team_name(team.name): team for team in Team.query.all()}
    
    # Process each fixture line
    fixtures_text = form.fixtures_text.data.strip().split('\n')
    for fixture_line in fixtures_text:
        if not fixture_line.strip():
            continue
                
        parts = [p.strip() for p in fixture_line.split('\t') if p.strip()]
        
        if len(parts) != 3:
            flash(f'Invalid line format: {fixture_line}', 'danger')
            error_count += 1
            continue

        try:
            # Parse fixture data
            gameweek_number = int(parts[0])
            home_team_name = normalize_team_name(parts[1])
            away_team_name = normalize_team_name(parts[2])
            
            # Validate gameweek number
            if gameweek_number < 1 or gameweek_number > 38:
                flash(f'Invalid gameweek number {gameweek_number}. Must be between 1 and 38.', 'danger')
                error_count += 1
                continue

            # Get correct gameweek
            correct_gameweek = gameweeks.get(gameweek_number)
            if not correct_gameweek:
                flash(f'Could not find gameweek number {gameweek_number}', 'danger')
                error_count += 1
                continue
            
            # Get teams
            home_team = all_teams.get(home_team_name)
            away_team = all_teams.get(away_team_name)
            
            if not home_team or not away_team:
                if not home_team:
                    flash(f'Could not find home team: "{parts[1]}"', 'danger')
                if not away_team:
                    flash(f'Could not find away team: "{parts[2]}"', 'danger')
                error_count += 1
                continue

            # Check for existing fixture
            existing = Fixture.query.filter_by(
                gameweek_id=correct_gameweek.id,
                home_team_id=home_team.id,
                away_team_id=away_team.id
            ).first()
            
            if existing:
                flash(f'Fixture already exists: GW{gameweek_number} - {parts[1]} vs {parts[2]}', 'warning')
                error_count += 1
                continue

            # Get next available ID
            result = db.session.execute(text("SELECT COALESCE(MAX(id), 0) + 1 FROM fixture"))
            next_id = result.scalar()
            
            # Create fixture
            fixture = Fixture(
                id=next_id,
                gameweek_id=correct_gameweek.id,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                division_id=form.division_id.data
            )
            
            db.session.add(fixture)
            db.session.flush()
            success_count += 1
            
        except Exception as e:
            current_app.logger.error(f'Error processing fixture: {str(e)}')
            current_app.logger.error(traceback.format_exc())
            error_count += 1
            continue

    # Commit successful fixtures
    if success_count > 0:
        try:
            db.session.commit()
            flash(f'Successfully added {success_count} fixtures.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving fixtures: {str(e)}', 'danger')
            current_app.logger.error(f'Error committing fixtures: {str(e)}')
            current_app.logger.error(traceback.format_exc())

    if error_count > 0:
        flash(f'Failed to add {error_count} fixtures. Check the error messages above.', 'warning')
        
    return render_template('admin/fixtures.html', form=form, fixtures=fixtures)