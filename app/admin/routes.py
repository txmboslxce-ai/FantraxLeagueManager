from flask import render_template, flash, redirect, url_for, current_app, request
from flask_login import login_required
from app import db
from app.admin import bp
from app.admin.forms import BulkFixtureForm
from app.admin.decorators import admin_required
from app.models import Season, Division, Gameweek, Team, Fixture
from app.utils import normalize_team_name
from sqlalchemy import text
import traceback

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

@bp.route('/divisions')
@login_required
@admin_required
def manage_divisions():
    current_season = Season.query.filter_by(is_current=True).first()
    if not current_season:
        flash('No current season found. Please create a season first.', 'warning')
        return redirect(url_for('admin.manage_seasons'))
        
    divisions = Division.query.filter_by(season_id=current_season.id).all()
    return render_template('admin/divisions.html', divisions=divisions, season=current_season)

@bp.route('/teams')
@login_required
@admin_required
def manage_teams():
    current_season = Season.query.filter_by(is_current=True).first()
    if not current_season:
        flash('No current season found. Please create a season first.', 'warning')
        return redirect(url_for('admin.manage_seasons'))
        
    teams = Team.query.all()
    return render_template('admin/teams.html', teams=teams)

@bp.route('/end-season')
@login_required
@admin_required
def end_season():
    current_season = Season.query.filter_by(is_current=True).first()
    if not current_season:
        flash('No current season found.', 'warning')
        return redirect(url_for('admin.manage_seasons'))
    return render_template('admin/end_season.html', season=current_season)

@bp.route('/upload-scores')
@login_required
@admin_required
def upload_scores():
    current_season = Season.query.filter_by(is_current=True).first()
    if not current_season:
        flash('No current season found. Please create a season first.', 'warning')
        return redirect(url_for('admin.manage_seasons'))
    return render_template('admin/scores.html', season=current_season)

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