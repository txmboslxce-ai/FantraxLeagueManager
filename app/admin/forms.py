from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateField, IntegerField, BooleanField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Optional, NumberRange, ValidationError
from app.models import Division, Team, Gameweek, Season

class DivisionForm(FlaskForm):
    name = StringField('Division Name', validators=[DataRequired()])
    submit = SubmitField('Save Division')

class TeamForm(FlaskForm):
    name = StringField('Team Name', validators=[DataRequired()])
    manager_name = StringField('Manager Name', validators=[DataRequired()])
    division_id = SelectField('Division', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Save Team')

class EditTeamForm(FlaskForm):
    name = StringField('Team Name', validators=[DataRequired()])
    manager_name = StringField('Manager Name', validators=[DataRequired()])
    submit = SubmitField('Update Team')

class BulkFixtureForm(FlaskForm):
    division_id = SelectField('Division', coerce=int, validators=[DataRequired()])
    fixtures_text = TextAreaField('Fixtures (Format: Gameweek[tab]Home Team[tab]Away Team - one per line)', 
                                validators=[DataRequired()])
    submit = SubmitField('Create Fixtures')

class ScoreUploadForm(FlaskForm):
    gameweek = SelectField('Gameweek', coerce=int, validators=[DataRequired()])
    division = SelectField('Division', coerce=int, validators=[DataRequired()])
    scores_text = TextAreaField('Scores (one per line)', validators=[DataRequired()],
                              render_kw={"rows": 10, "placeholder": "Home Team    Home Score    Away Team    Away Score"})
    submit = SubmitField('Upload Scores')

class CupCompetitionForm(FlaskForm):
    name = StringField('Competition Name', validators=[DataRequired()])
    has_groups = BooleanField('Use Group Stage Format')
    num_groups = IntegerField('Number of Groups', default=12, 
                            validators=[Optional(), NumberRange(min=1, max=26, message="Number of groups must be between 1 and 26")])
    teams_per_group = IntegerField('Teams per Group', default=3,
                                validators=[Optional(), NumberRange(min=2, message="Must have at least 2 teams per group")])
    submit = SubmitField('Create Cup Competition')

class CupGroupTeamForm(FlaskForm):
    team_id = SelectField('Team', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Add Team to Group')

class CupGroupMatchForm(FlaskForm):
    home_team_id = SelectField('Home Team', coerce=int, validators=[DataRequired()])
    away_team_id = SelectField('Away Team', coerce=int, validators=[DataRequired()])
    gameweek_id = SelectField('Gameweek', coerce=int, validators=[Optional()])
    submit = SubmitField('Create Match')

class TitleForm(FlaskForm):
    team_id = SelectField('Team', coerce=int, validators=[DataRequired()])
    season_id = SelectField('Season', coerce=int, validators=[DataRequired()])
    type = SelectField('Title Type', 
                      choices=[('cup', 'Cup'), ('league', 'League')], 
                      validators=[DataRequired()])
    division_id = SelectField('Division', coerce=int)
    is_runner_up = BooleanField('Runner Up')
    submit = SubmitField('Add Title')

class EditCupGroupMatchForm(FlaskForm):
    gameweek_id = SelectField('Gameweek', coerce=int, validators=[Optional()])
    submit = SubmitField('Update Match')

class CupRoundForm(FlaskForm):
    name = StringField('Round Name', validators=[DataRequired()])
    order = IntegerField('Round Order', validators=[DataRequired()])
    num_matches = IntegerField('Number of Matches', validators=[DataRequired()])
    first_leg_gameweek_id = SelectField('First Leg Gameweek', coerce=int, validators=[DataRequired()])
    second_leg_gameweek_id = SelectField('Second Leg Gameweek', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Create Round')

class CupMatchForm(FlaskForm):
    match_id = HiddenField()
    home_team_id = SelectField('Home Team', coerce=int, validators=[DataRequired()])
    away_team_id = SelectField('Away Team', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Update Match')

class ManagerMonthForm(FlaskForm):
    name = StringField('Month Name', validators=[DataRequired()])
    start_gameweek_id = SelectField('Start Gameweek', coerce=int, validators=[DataRequired()])
    end_gameweek_id = SelectField('End Gameweek', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Create Manager Month')

class SeasonForm(FlaskForm):
    name = StringField('Season Name', validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    is_current = BooleanField('Current Season')
    submit = SubmitField('Create Season')

class EditSeasonForm(FlaskForm):
    name = StringField('Season Name', validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    is_current = BooleanField('Current Season')
    submit = SubmitField('Update Season')

class EndSeasonForm(FlaskForm):
    confirm = BooleanField('I confirm I want to end the current season', validators=[DataRequired()])
    submit = SubmitField('End Season')

class RulesForm(FlaskForm):
    content = TextAreaField('Rules Content', validators=[DataRequired()])
    submit  = SubmitField('Save')