from flask import render_template, flash, redirect, url_for, current_app, request
from flask_login import login_required
from app import db
from app.admin import bp
from app.admin.forms import BulkFixtureForm
from app.admin.decorators import admin_required
from app.models import Season, Division, Gameweek, Team, Fixture
from app.utils import normalize_team_name
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

@bp.route('/fixtures', methods=['GET', 'POST'])
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
    
    try:
        if current_app.debug and request.method == 'POST':
            current_app.logger.info(f'POST data: {request.form.to_dict()}')
            
        current_season = Season.query.filter_by(is_current=True).first()
        if not current_season:
            error_msg = "No current season found. Please create a season first."
            log_error(error_msg)
            flash(error_msg, 'warning')
            return redirect(url_for('admin.manage_seasons'))

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
                
            success_count = 0
            error_count = 0
            fixtures_text = form.fixtures_text.data.strip().split('\n')
            
            all_gameweeks = Gameweek.query.filter_by(season_id=current_season.id).all()
            gameweeks = {gw.number: gw for gw in all_gameweeks}
            
            if not gameweeks:
                error_msg = "No gameweeks found for the current season."
                log_error(error_msg)
                flash(error_msg, 'danger')
                return redirect(url_for('admin.manage_fixtures'))
                
            available_numbers = sorted([gw.number for gw in all_gameweeks])
            current_app.logger.info(f'Available gameweek numbers: {available_numbers}')

            all_teams = {normalize_team_name(team.name): team for team in Team.query.all()}
            
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
                    home_team_name = normalize_team_name(parts[1])
                    away_team_name = normalize_team_name(parts[2])
                    
                    if gameweek_number < 1 or gameweek_number > 38:
                        error_msg = f'Invalid gameweek number {gameweek_number}. Must be between 1 and 38.'
                        log_error(error_msg)
                        flash(error_msg, 'danger')
                        error_count += 1
                        continue

                    correct_gameweek = gameweeks.get(gameweek_number)
                    if not correct_gameweek:
                        error_msg = f'Could not find gameweek number {gameweek_number}'
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

                    existing = Fixture.query.filter_by(
                        gameweek_id=correct_gameweek.id,
                        home_team_id=home_team.id,
                        away_team_id=away_team.id
                    ).first()
                    
                    if existing:
                        error_msg = f'Fixture already exists: GW{gameweek_number} - {parts[1]} vs {parts[2]}'
                        log_error(error_msg)
                        flash(error_msg, 'warning')
                        error_count += 1
                        continue

                    try:
                        fixture = Fixture(
                            gameweek_id=correct_gameweek.id,
                            home_team_id=home_team.id,
                            away_team_id=away_team.id,
                            division_id=form.division_id.data
                        )
                        db.session.add(fixture)
                        db.session.flush()
                        success_count += 1
                    except Exception as e:
                        error_msg = f'Error creating fixture: {str(e)}'
                        current_app.logger.error(error_msg)
                        db.session.rollback()
                        flash(error_msg, 'danger')
                        error_count += 1
                        continue

                except ValueError as e:
                    error_msg = f'Invalid gameweek number in line: {fixture_line}'
                    log_error(e, error_msg)
                    flash(error_msg, 'danger')
                    error_count += 1
                    continue

            if success_count > 0:
                try:
                    db.session.commit()
                    flash(f'Successfully added {success_count} fixtures.', 'success')
                except Exception as e:
                    error_msg = f'Error committing fixtures to database: {str(e)}'
                    log_error(e, error_msg)
                    db.session.rollback()
                    flash(error_msg, 'danger')

            if error_count > 0:
                flash(f'Failed to add {error_count} fixtures. Check the error messages above.', 'warning')

    except Exception as e:
        error_msg = log_error(e)
        flash(error_msg, 'danger')
        
    return render_template('admin/fixtures.html', form=form, fixtures=fixtures)