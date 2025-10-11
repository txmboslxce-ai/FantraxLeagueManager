from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import or_
from app import db, login_manager
from app.utils import normalize_team_name

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        
    def check_password(self, password):
        print(f"Checking password for user: {self.username}")
        print(f"Stored hash: {self.password_hash}")
        print(f"Testing password: {password}")
        result = check_password_hash(self.password_hash, password)
        print(f"Password check result: {result}")
        return result

class Season(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_current = db.Column(db.Boolean, default=False)
    divisions = db.relationship('Division', backref='season', lazy=True)
    cup_competitions = db.relationship('CupCompetition', backref='season', lazy=True)
    team_seasons = db.relationship('TeamSeason', backref='season', lazy=True)

class Division(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    season_id = db.Column(db.Integer, db.ForeignKey('season.id'), nullable=False)
    teams = db.relationship('TeamSeason', backref='division', lazy=True)
    
    @property
    def order(self):
        """Return a numerical order for consistent sorting of divisions"""
        order_map = {
            'Premier League': 1,
            'Championship': 2,
            'League One': 3
        }
        return order_map.get(self.name, 99)

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    _name = db.Column('name', db.String(64), unique=True, nullable=False)
    manager_name = db.Column(db.String(64), nullable=False)
    seasons = db.relationship('TeamSeason', backref='team', lazy=True)
    titles = db.relationship('Title', backref='team', lazy=True)
    manager_of_the_month_awards = db.relationship('ManagerOfTheMonth', backref='team', lazy=True)
    
    @property
    def name(self):
        return self._name
        
    @name.setter
    def name(self, value):
        self._name = normalize_team_name(value)

class TeamSeason(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    season_id = db.Column(db.Integer, db.ForeignKey('season.id'), nullable=False)
    division_id = db.Column(db.Integer, db.ForeignKey('division.id'), nullable=False)
    points = db.Column(db.Integer, default=0)
    total_score = db.Column(db.Float, default=0.0)
    position = db.Column(db.Integer)
    
    def recalculate_totals(self):
        """Recalculate total scores and points based on all fixtures"""
        fixtures = Fixture.query.join(
            Gameweek, Fixture.gameweek_id == Gameweek.id
        ).filter(
            Gameweek.season_id == self.season_id,
            or_(
                Fixture.home_team_id == self.team_id,
                Fixture.away_team_id == self.team_id
            ),
            Fixture.home_score.isnot(None),
            Fixture.away_score.isnot(None)
        ).all()
        
        self.total_score = 0.0
        self.points = 0
        
        for fixture in fixtures:
            if fixture.home_team_id == self.team_id:
                self.total_score += fixture.home_score
                if fixture.home_score > fixture.away_score:
                    self.points += 3
                elif fixture.home_score == fixture.away_score:
                    self.points += 1
            else:
                self.total_score += fixture.away_score
                if fixture.away_score > fixture.home_score:
                    self.points += 3
                elif fixture.home_score == fixture.away_score:
                    self.points += 1
    
    @property
    def fixtures(self):
        return Fixture.query.join(
            Gameweek, Fixture.gameweek_id == Gameweek.id
        ).filter(
            Gameweek.season_id == self.season_id,
            or_(
                Fixture.home_team_id == self.team_id,
                Fixture.away_team_id == self.team_id
            )
        ).order_by(Gameweek.number).all()
    
    @property
    def played_matches(self):
        return Fixture.query.join(
            Gameweek, Fixture.gameweek_id == Gameweek.id
        ).filter(
            Gameweek.season_id == self.season_id,
            or_(
                Fixture.home_team_id == self.team_id,
                Fixture.away_team_id == self.team_id
            ),
            Fixture.home_score.isnot(None),
            Fixture.away_score.isnot(None)
        ).count()
    
    @property
    def wins(self):
        played_fixtures = Fixture.query.join(
            Gameweek, Fixture.gameweek_id == Gameweek.id
        ).filter(
            Gameweek.season_id == self.season_id,
            or_(
                Fixture.home_team_id == self.team_id,
                Fixture.away_team_id == self.team_id
            ),
            Fixture.home_score.isnot(None),
            Fixture.away_score.isnot(None)
        ).all()
        
        return sum(1 for f in played_fixtures if 
                  (f.home_team_id == self.team_id and f.home_score > f.away_score) or
                  (f.away_team_id == self.team_id and f.away_score > f.home_score))
    
    @property
    def draws(self):
        played_fixtures = Fixture.query.join(
            Gameweek, Fixture.gameweek_id == Gameweek.id
        ).filter(
            Gameweek.season_id == self.season_id,
            or_(
                Fixture.home_team_id == self.team_id,
                Fixture.away_team_id == self.team_id
            ),
            Fixture.home_score.isnot(None),
            Fixture.away_score.isnot(None)
        ).all()
        
        return sum(1 for f in played_fixtures if f.home_score == f.away_score)
    
    @property
    def losses(self):
        played_fixtures = Fixture.query.join(
            Gameweek, Fixture.gameweek_id == Gameweek.id
        ).filter(
            Gameweek.season_id == self.season_id,
            or_(
                Fixture.home_team_id == self.team_id,
                Fixture.away_team_id == self.team_id
            ),
            Fixture.home_score.isnot(None),
            Fixture.away_score.isnot(None)
        ).all()
        
        return sum(1 for f in played_fixtures if 
                  (f.home_team_id == self.team_id and f.home_score < f.away_score) or
                  (f.away_team_id == self.team_id and f.away_score < f.home_score))
    
    @property
    def goals_for(self):
        played_fixtures = Fixture.query.join(
            Gameweek, Fixture.gameweek_id == Gameweek.id
        ).filter(
            Gameweek.season_id == self.season_id,
            or_(
                Fixture.home_team_id == self.team_id,
                Fixture.away_team_id == self.team_id
            ),
            Fixture.home_score.isnot(None),
            Fixture.away_score.isnot(None)
        ).all()
        
        return sum(f.home_score if f.home_team_id == self.team_id else f.away_score 
                  for f in played_fixtures)
    
    @property
    def goals_against(self):
        played_fixtures = Fixture.query.join(
            Gameweek, Fixture.gameweek_id == Gameweek.id
        ).filter(
            Gameweek.season_id == self.season_id,
            or_(
                Fixture.home_team_id == self.team_id,
                Fixture.away_team_id == self.team_id
            ),
            Fixture.home_score.isnot(None),
            Fixture.away_score.isnot(None)
        ).all()
        
        return sum(f.away_score if f.home_team_id == self.team_id else f.home_score 
                  for f in played_fixtures)
    
    @property
    def recent_form(self):
        recent_fixtures = Fixture.query.join(
            Gameweek, Fixture.gameweek_id == Gameweek.id
        ).filter(
            Gameweek.season_id == self.season_id,
            or_(
                Fixture.home_team_id == self.team_id,
                Fixture.away_team_id == self.team_id
            ),
            Fixture.home_score.isnot(None),
            Fixture.away_score.isnot(None)
        ).order_by(Gameweek.number.desc()).limit(5).all()
        
        form = []
        for fixture in recent_fixtures:
            if fixture.home_team_id == self.team_id:
                if fixture.home_score > fixture.away_score:
                    form.append('W')
                elif fixture.home_score < fixture.away_score:
                    form.append('L')
                else:
                    form.append('D')
            else:
                if fixture.away_score > fixture.home_score:
                    form.append('W')
                elif fixture.away_score < fixture.home_score:
                    form.append('L')
                else:
                    form.append('D')
        return form

class Gameweek(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False)
    season_id = db.Column(db.Integer, db.ForeignKey('season.id'), nullable=False)
    deadline = db.Column(db.DateTime, nullable=False)
    is_current = db.Column(db.Boolean, default=False)
    fixtures = db.relationship('Fixture', backref='gameweek', lazy=True)

class Fixture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gameweek_id = db.Column(db.Integer, db.ForeignKey('gameweek.id'), nullable=False)
    home_team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    home_score = db.Column(db.Float)
    away_score = db.Column(db.Float)
    division_id = db.Column(db.Integer, db.ForeignKey('division.id'), nullable=False)
    
    # Add relationships
    home_team = db.relationship('Team', foreign_keys=[home_team_id], backref='home_fixtures')
    away_team = db.relationship('Team', foreign_keys=[away_team_id], backref='away_fixtures')
    division = db.relationship('Division', backref='fixtures')

class CupCompetition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    season_id = db.Column(db.Integer, db.ForeignKey('season.id'), nullable=False)
    has_groups = db.Column(db.Boolean, default=False)  # New format with groups
    num_groups = db.Column(db.Integer, default=12)  # Number of groups
    teams_per_group = db.Column(db.Integer, default=3)  # Teams per group
    rounds = db.relationship('CupRound', backref='competition', lazy=True)
    groups = db.relationship('CupGroup', backref='competition', lazy=True, cascade='all, delete-orphan')
    
    def create_initial_groups(self):
        """Create the initial empty groups for the competition"""
        if self.has_groups and not self.groups:
            # Create group names dynamically based on num_groups
            from string import ascii_uppercase
            group_names = list(ascii_uppercase[:self.num_groups])
            
            try:
                for i in range(self.num_groups):
                    group = CupGroup(
                        competition_id=self.id,
                        name=f"Group {group_names[i]}" if i < len(group_names) else f"Group {i + 1}",
                        order=i + 1
                    )
                    db.session.add(group)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                raise Exception(f"Error creating groups: {str(e)}")
    
    @property
    def group_stage_complete(self):
        """Check if all group stage matches are complete"""
        if not self.has_groups:
            return False
        
        for group in self.groups:
            for match in group.matches:
                if match.home_score is None or match.away_score is None:
                    return False
        return True
    
    def get_group_winners(self):
        """Get first place teams from all groups, sorted by points then points for"""
        if not self.has_groups:
            return []
        
        winners = []
        for group in self.groups:
            table = group.group_table
            if table:
                winner = table[0]  # First place team
                winners.append({
                    'team': winner['team'],
                    'group': group,
                    'points': winner['points'],
                    'goals_for': winner['goals_for'],
                    'goal_difference': winner['goal_difference']
                })
        
        # Sort by points, then goals for to determine top 8 for direct qualification
        winners.sort(key=lambda x: (-x['points'], -x['goals_for']))
        return winners
    
    def get_playoff_teams(self):
        """Get teams that go to playoff round (bottom 4 group winners + all second place teams)"""
        if not self.has_groups:
            return []
        
        winners = self.get_group_winners()
        playoff_teams = []
        
        # Bottom 4 group winners (positions 8-11 in sorted list)
        if len(winners) >= 8:
            playoff_teams.extend(winners[8:])
        
        # All second place teams
        for group in self.groups:
            table = group.group_table
            if len(table) >= 2:
                second_place = table[1]  # Second place team
                playoff_teams.append({
                    'team': second_place['team'],
                    'group': group,
                    'points': second_place['points'],
                    'goals_for': second_place['goals_for'],
                    'goal_difference': second_place['goal_difference'],
                    'position': 'Second'
                })
        
        return playoff_teams
    
    def get_direct_qualifiers(self):
        """Get top 8 group winners who go directly to Round of 16"""
        winners = self.get_group_winners()
        return winners[:8] if len(winners) >= 8 else winners

class CupRound(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    competition_id = db.Column(db.Integer, db.ForeignKey('cup_competition.id'), nullable=False)
    order = db.Column(db.Integer, nullable=False)
    first_leg_gameweek_id = db.Column(db.Integer, db.ForeignKey('gameweek.id'))
    second_leg_gameweek_id = db.Column(db.Integer, db.ForeignKey('gameweek.id'))
    num_matches = db.Column(db.Integer, nullable=False)  # Number of matches in this round
    matches = db.relationship('CupMatch', backref='round', lazy=True)
    
    # Add relationships for gameweeks
    first_leg_gameweek = db.relationship('Gameweek', foreign_keys=[first_leg_gameweek_id])
    second_leg_gameweek = db.relationship('Gameweek', foreign_keys=[second_leg_gameweek_id])
    
    @property
    def is_complete(self):
        """Check if all matches in this round have winners"""
        return all(match.winner_id is not None for match in self.matches)
    
    @property
    def winners(self):
        """Get all winners from this round"""
        return [match.winner for match in self.matches if match.winner_id is not None]

class CupMatch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey('cup_round.id'), nullable=False)
    home_team_id = db.Column(db.Integer, db.ForeignKey('team.id'))
    away_team_id = db.Column(db.Integer, db.ForeignKey('team.id'))
    first_leg_home_score = db.Column(db.Float)
    first_leg_away_score = db.Column(db.Float)
    second_leg_home_score = db.Column(db.Float)
    second_leg_away_score = db.Column(db.Float)
    winner_id = db.Column(db.Integer, db.ForeignKey('team.id'))

    # Relationships
    home_team = db.relationship('Team', foreign_keys=[home_team_id], backref='home_cup_matches')
    away_team = db.relationship('Team', foreign_keys=[away_team_id], backref='away_cup_matches')
    winner    = db.relationship('Team', foreign_keys=[winner_id],    backref='cup_wins')

    @property
    def first_leg_complete(self):
        return (
            self.first_leg_home_score is not None
            and self.first_leg_away_score is not None
        )

    @property
    def second_leg_complete(self):
        return (
            self.second_leg_home_score is not None
            and self.second_leg_away_score is not None
        )

    @property
    def aggregate_home_score(self):
        if not self.first_leg_complete:
            return None
        total = self.first_leg_home_score
        if self.second_leg_complete:
            # correctly add home side's second-leg score
            total += self.second_leg_home_score
        return total

    @property
    def aggregate_away_score(self):
        if not self.first_leg_complete:
            return None
        total = self.first_leg_away_score
        if self.second_leg_complete:
            # correctly add away side's second-leg score
            total += self.second_leg_away_score
        return total

    def update_scores_from_fixtures(self):
        """Update cup match scores from league fixtures"""
        # First leg
        if self.round.first_leg_gameweek:
            # home side
            first_leg = Fixture.query.filter(
                Fixture.gameweek_id == self.round.first_leg_gameweek_id,
                ((Fixture.home_team_id == self.home_team_id) |
                 (Fixture.away_team_id == self.home_team_id))
            ).first()
            if first_leg and first_leg.home_score is not None:
                if first_leg.home_team_id == self.home_team_id:
                    self.first_leg_home_score = first_leg.home_score
                else:
                    self.first_leg_home_score = first_leg.away_score

            # away side
            first_leg = Fixture.query.filter(
                Fixture.gameweek_id == self.round.first_leg_gameweek_id,
                ((Fixture.home_team_id == self.away_team_id) |
                 (Fixture.away_team_id == self.away_team_id))
            ).first()
            if first_leg and first_leg.home_score is not None:
                if first_leg.home_team_id == self.away_team_id:
                    self.first_leg_away_score = first_leg.home_score
                else:
                    self.first_leg_away_score = first_leg.away_score

        # Second leg
        if self.round.second_leg_gameweek:
            # home side
            second_leg = Fixture.query.filter(
                Fixture.gameweek_id == self.round.second_leg_gameweek_id,
                ((Fixture.home_team_id == self.home_team_id) |
                 (Fixture.away_team_id == self.home_team_id))
            ).first()
            if second_leg and second_leg.home_score is not None:
                if second_leg.home_team_id == self.home_team_id:
                    self.second_leg_home_score = second_leg.home_score
                else:
                    self.second_leg_home_score = second_leg.away_score

            # away side
            second_leg = Fixture.query.filter(
                Fixture.gameweek_id == self.round.second_leg_gameweek_id,
                ((Fixture.home_team_id == self.away_team_id) |
                 (Fixture.away_team_id == self.away_team_id))
            ).first()
            if second_leg and second_leg.home_score is not None:
                if second_leg.home_team_id == self.away_team_id:
                    self.second_leg_away_score = second_leg.home_score
                else:
                    self.second_leg_away_score = second_leg.away_score

        # Determine winner if both legs complete
        if self.first_leg_complete and self.second_leg_complete:
            if self.aggregate_home_score > self.aggregate_away_score:
                self.winner_id = self.home_team_id
            elif self.aggregate_away_score > self.aggregate_home_score:
                self.winner_id = self.away_team_id

class CupGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    competition_id = db.Column(db.Integer, db.ForeignKey('cup_competition.id'), nullable=False)
    name = db.Column(db.String(64), nullable=False)  # e.g., "Group A", "Group B"
    order = db.Column(db.Integer, nullable=False)  # 1-12 for sorting
    
    # Relationships
    teams = db.relationship('CupGroupTeam', backref='group', lazy=True)
    matches = db.relationship('CupGroupMatch', backref='group', lazy=True)
    
    @property
    def group_table(self):
        """Get the group table with points, goals for/against"""
        teams = {}
        
        # Initialize team stats
        for team_entry in self.teams:
            teams[team_entry.team_id] = {
                'team': team_entry.team,
                'played': 0,
                'won': 0,
                'drawn': 0,
                'lost': 0,
                'goals_for': 0,
                'goals_against': 0,
                'goal_difference': 0,
                'points': 0
            }
        
        # Calculate stats from matches
        for match in self.matches:
            if match.home_score is not None and match.away_score is not None:
                home_stats = teams[match.home_team_id]
                away_stats = teams[match.away_team_id]
                
                # Update played
                home_stats['played'] += 1
                away_stats['played'] += 1
                
                # Update goals
                home_stats['goals_for'] += match.home_score
                home_stats['goals_against'] += match.away_score
                away_stats['goals_for'] += match.away_score
                away_stats['goals_against'] += match.home_score
                
                # Update results and points
                if match.home_score > match.away_score:
                    home_stats['won'] += 1
                    home_stats['points'] += 3
                    away_stats['lost'] += 1
                elif match.away_score > match.home_score:
                    away_stats['won'] += 1
                    away_stats['points'] += 3
                    home_stats['lost'] += 1
                else:
                    home_stats['drawn'] += 1
                    home_stats['points'] += 1
                    away_stats['drawn'] += 1
                    away_stats['points'] += 1
        
        # Calculate goal difference
        for team_stats in teams.values():
            team_stats['goal_difference'] = team_stats['goals_for'] - team_stats['goals_against']
        
        # Sort by points, then goal difference, then goals for
        sorted_teams = sorted(teams.values(), 
                            key=lambda x: (-x['points'], -x['goal_difference'], -x['goals_for']))
        
        return sorted_teams

class CupGroupTeam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('cup_group.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    
    # Relationships
    team = db.relationship('Team', backref='cup_group_entries')

class CupGroupMatch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('cup_group.id'), nullable=False)
    home_team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    gameweek_id = db.Column(db.Integer, db.ForeignKey('gameweek.id'))  # Made optional
    home_score = db.Column(db.Float)
    away_score = db.Column(db.Float)
    
    # Relationships
    home_team = db.relationship('Team', foreign_keys=[home_team_id])
    away_team = db.relationship('Team', foreign_keys=[away_team_id])
    gameweek = db.relationship('Gameweek', backref='cup_group_matches')
    
    def update_scores_from_fixtures(self):
        """Update group match scores from league fixtures"""
        if not self.gameweek_id:
            return  # Can't update scores without a gameweek
            
        # Find the fixture for the home team in this gameweek
        home_fixture = Fixture.query.filter(
            Fixture.gameweek_id == self.gameweek_id,
            ((Fixture.home_team_id == self.home_team_id) |
             (Fixture.away_team_id == self.home_team_id))
        ).first()
        
        # Find the fixture for the away team in this gameweek
        away_fixture = Fixture.query.filter(
            Fixture.gameweek_id == self.gameweek_id,
            ((Fixture.home_team_id == self.away_team_id) |
             (Fixture.away_team_id == self.away_team_id))
        ).first()
        
        if home_fixture and home_fixture.home_score is not None:
            if home_fixture.home_team_id == self.home_team_id:
                self.home_score = home_fixture.home_score
            else:
                self.home_score = home_fixture.away_score
                
        if away_fixture and away_fixture.home_score is not None:
            if away_fixture.home_team_id == self.away_team_id:
                self.away_score = away_fixture.home_score
            else:
                self.away_score = away_fixture.away_score

class ManagerMonth(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    season_id = db.Column(db.Integer, db.ForeignKey('season.id'), nullable=False)
    start_gameweek_id = db.Column(db.Integer, db.ForeignKey('gameweek.id'), nullable=False)
    end_gameweek_id = db.Column(db.Integer, db.ForeignKey('gameweek.id'), nullable=False)
    winner_id = db.Column(db.Integer, db.ForeignKey('team.id'))
    
    # Relationships
    season = db.relationship('Season', backref='manager_months')
    start_gameweek = db.relationship('Gameweek', foreign_keys=[start_gameweek_id])
    end_gameweek = db.relationship('Gameweek', foreign_keys=[end_gameweek_id])
    winner = db.relationship('Team', foreign_keys=[winner_id], backref='motm_wins')
    
    @property
    def gameweeks(self):
        """Get all gameweeks in this month's range."""
        return Gameweek.query.filter(
            Gameweek.season_id == self.season_id,
            Gameweek.number >= self.start_gameweek.number,
            Gameweek.number <= self.end_gameweek.number
        ).order_by(Gameweek.number).all()
    
    @property
    def has_fixtures(self):
        """Check if all fixtures in all gameweeks for this month have scores."""
        gameweeks = self.gameweeks
        
        for gameweek in gameweeks:
            # Count fixtures with scores for this gameweek
            fixtures_with_scores = Fixture.query.filter(
                Fixture.gameweek_id == gameweek.id,
                Fixture.home_score.isnot(None),
                Fixture.away_score.isnot(None)
            ).count()
            
            # Each gameweek should have 12 fixtures (6 per division)
            if fixtures_with_scores < 12:
                return False
        
        return True
    
    def get_team_stats(self, team_id):
        """Get a team's stats for this month."""
        fixtures = Fixture.query.join(
            Gameweek
        ).filter(
            Gameweek.season_id == self.season_id,
            Gameweek.number >= self.start_gameweek.number,
            Gameweek.number <= self.end_gameweek.number,
            or_(
                Fixture.home_team_id == team_id,
                Fixture.away_team_id == team_id
            ),
            Fixture.home_score.isnot(None),
            Fixture.away_score.isnot(None)
        ).all()
        
        stats = {
            'played': len(fixtures),
            'wins': 0,
            'draws': 0,
            'losses': 0,
            'goals_for': 0.0,
            'goals_against': 0.0,
            'points': 0
        }
        
        for fixture in fixtures:
            if fixture.home_team_id == team_id:
                stats['goals_for'] += fixture.home_score
                stats['goals_against'] += fixture.away_score
                if fixture.home_score > fixture.away_score:
                    stats['wins'] += 1
                    stats['points'] += 3
                elif fixture.home_score == fixture.away_score:
                    stats['draws'] += 1
                    stats['points'] += 1
                else:
                    stats['losses'] += 1
            else:
                stats['goals_for'] += fixture.away_score
                stats['goals_against'] += fixture.home_score
                if fixture.away_score > fixture.home_score:
                    stats['wins'] += 1
                    stats['points'] += 3
                elif fixture.away_score == fixture.home_score:
                    stats['draws'] += 1
                    stats['points'] += 1
                else:
                    stats['losses'] += 1
        
        stats['goal_difference'] = stats['goals_for'] - stats['goals_against']
        return stats
    
    def get_standings(self):
        """Get all team standings for this month."""
        # Get all teams that played in this month
        teams = Team.query.join(
            Fixture, or_(
                Fixture.home_team_id == Team.id,
                Fixture.away_team_id == Team.id
            )
        ).join(
            Gameweek, Fixture.gameweek_id == Gameweek.id
        ).filter(
            Gameweek.season_id == self.season_id,
            Gameweek.number >= self.start_gameweek.number,
            Gameweek.number <= self.end_gameweek.number,
            Fixture.home_score.isnot(None),
            Fixture.away_score.isnot(None)
        ).distinct().all()
        
        # Calculate stats for each team
        standings = []
        for team in teams:
            stats = self.get_team_stats(team.id)
            standings.append({
                'team': team,
                **stats
            })
        
        # Sort by points, goal difference, then goals for
        return sorted(
            standings,
            key=lambda x: (-x['points'], -x['goals_for'])
        )

class ManagerOfTheMonth(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    manager_month_id = db.Column(db.Integer, db.ForeignKey('manager_month.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    total_score = db.Column(db.Float, nullable=False)
    
    # Add relationships
    month = db.relationship('ManagerMonth', backref='awards')

class Title(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    season_id = db.Column(db.Integer, db.ForeignKey('season.id'), nullable=False)
    type = db.Column(db.String(64), nullable=False)  # 'league' or 'cup'
    division_id = db.Column(db.Integer, db.ForeignKey('division.id'))  # for league titles
    cup_competition_id = db.Column(db.Integer, db.ForeignKey('cup_competition.id'))  # for cup titles
    is_runner_up = db.Column(db.Boolean, default=False) 
    season = db.relationship('Season', backref='titles')
    division = db.relationship('Division', backref='titles')
    cup_competition = db.relationship('CupCompetition', backref='titles')

class Rule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)