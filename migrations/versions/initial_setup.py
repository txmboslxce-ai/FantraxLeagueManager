"""Initial database setup

Revision ID: initial_setup
Revises: 
Create Date: 2024-03-21 16:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'initial_setup'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create user table
    op.create_table('user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('password_hash', sa.String(length=128), nullable=True),
        sa.Column('is_admin', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )

    # Create season table
    op.create_table('season',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('is_current', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create division table
    op.create_table('division',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['season_id'], ['season.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create team table
    op.create_table('team',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('manager_name', sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create gameweek table
    op.create_table('gameweek',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('number', sa.Integer(), nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=False),
        sa.Column('deadline', sa.DateTime(), nullable=False),
        sa.Column('is_current', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['season_id'], ['season.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create cup_competition table
    op.create_table('cup_competition',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['season_id'], ['season.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create cup_round table
    op.create_table('cup_round',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('competition_id', sa.Integer(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('first_leg_gameweek_id', sa.Integer(), nullable=True),
        sa.Column('second_leg_gameweek_id', sa.Integer(), nullable=True),
        sa.Column('num_matches', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['competition_id'], ['cup_competition.id'], ),
        sa.ForeignKeyConstraint(['first_leg_gameweek_id'], ['gameweek.id'], ),
        sa.ForeignKeyConstraint(['second_leg_gameweek_id'], ['gameweek.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create team_season table
    op.create_table('team_season',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=False),
        sa.Column('division_id', sa.Integer(), nullable=False),
        sa.Column('points', sa.Integer(), nullable=True),
        sa.Column('total_score', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['division_id'], ['division.id'], ),
        sa.ForeignKeyConstraint(['season_id'], ['season.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['team.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create fixture table
    op.create_table('fixture',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('gameweek_id', sa.Integer(), nullable=False),
        sa.Column('home_team_id', sa.Integer(), nullable=False),
        sa.Column('away_team_id', sa.Integer(), nullable=False),
        sa.Column('home_score', sa.Float(), nullable=True),
        sa.Column('away_score', sa.Float(), nullable=True),
        sa.Column('division_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['away_team_id'], ['team.id'], ),
        sa.ForeignKeyConstraint(['division_id'], ['division.id'], ),
        sa.ForeignKeyConstraint(['gameweek_id'], ['gameweek.id'], ),
        sa.ForeignKeyConstraint(['home_team_id'], ['team.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create cup_match table
    op.create_table('cup_match',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('round_id', sa.Integer(), nullable=False),
        sa.Column('home_team_id', sa.Integer(), nullable=True),
        sa.Column('away_team_id', sa.Integer(), nullable=True),
        sa.Column('first_leg_home_score', sa.Float(), nullable=True),
        sa.Column('first_leg_away_score', sa.Float(), nullable=True),
        sa.Column('second_leg_home_score', sa.Float(), nullable=True),
        sa.Column('second_leg_away_score', sa.Float(), nullable=True),
        sa.Column('winner_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['away_team_id'], ['team.id'], ),
        sa.ForeignKeyConstraint(['home_team_id'], ['team.id'], ),
        sa.ForeignKeyConstraint(['round_id'], ['cup_round.id'], ),
        sa.ForeignKeyConstraint(['winner_id'], ['team.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create manager_month table
    op.create_table('manager_month',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=False),
        sa.Column('start_gameweek_id', sa.Integer(), nullable=False),
        sa.Column('end_gameweek_id', sa.Integer(), nullable=False),
        sa.Column('winner_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['end_gameweek_id'], ['gameweek.id'], ),
        sa.ForeignKeyConstraint(['season_id'], ['season.id'], ),
        sa.ForeignKeyConstraint(['start_gameweek_id'], ['gameweek.id'], ),
        sa.ForeignKeyConstraint(['winner_id'], ['team.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create manager_of_the_month table
    op.create_table('manager_of_the_month',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('manager_month_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('total_score', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['manager_month_id'], ['manager_month.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['team.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create title table
    op.create_table('title',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=64), nullable=False),
        sa.Column('division_id', sa.Integer(), nullable=True),
        sa.Column('cup_competition_id', sa.Integer(), nullable=True),
        sa.Column('is_runner_up', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['cup_competition_id'], ['cup_competition.id'], ),
        sa.ForeignKeyConstraint(['division_id'], ['division.id'], ),
        sa.ForeignKeyConstraint(['season_id'], ['season.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['team.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('title')
    op.drop_table('manager_of_the_month')
    op.drop_table('manager_month')
    op.drop_table('cup_match')
    op.drop_table('fixture')
    op.drop_table('team_season')
    op.drop_table('cup_round')
    op.drop_table('cup_competition')
    op.drop_table('gameweek')
    op.drop_table('team')
    op.drop_table('division')
    op.drop_table('season')
    op.drop_table('user') 