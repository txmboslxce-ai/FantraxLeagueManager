"""Add sequences for PostgreSQL auto-incrementing IDs

Revision ID: add_sequences
Revises: efbd5466da3b
Create Date: 2025-10-12 17:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_sequences'
down_revision = 'efbd5466da3b'
branch_labels = None
depends_on = None

def upgrade():
    # Create sequences for all tables that need auto-incrementing IDs
    op.execute("""
    DO $$
    BEGIN
        -- Create sequences if they don't exist
        CREATE SEQUENCE IF NOT EXISTS fixture_id_seq;
        CREATE SEQUENCE IF NOT EXISTS cup_match_id_seq;
        CREATE SEQUENCE IF NOT EXISTS cup_group_id_seq;
        CREATE SEQUENCE IF NOT EXISTS cup_group_team_id_seq;
        CREATE SEQUENCE IF NOT EXISTS cup_group_match_id_seq;
        CREATE SEQUENCE IF NOT EXISTS rule_id_seq;
        
        -- Set the sequences to be owned by their respective table columns
        ALTER TABLE fixture ALTER COLUMN id SET DEFAULT nextval('fixture_id_seq');
        ALTER TABLE cup_match ALTER COLUMN id SET DEFAULT nextval('cup_match_id_seq');
        ALTER TABLE cup_group ALTER COLUMN id SET DEFAULT nextval('cup_group_id_seq');
        ALTER TABLE cup_group_team ALTER COLUMN id SET DEFAULT nextval('cup_group_team_id_seq');
        ALTER TABLE cup_group_match ALTER COLUMN id SET DEFAULT nextval('cup_group_match_id_seq');
        ALTER TABLE rule ALTER COLUMN id SET DEFAULT nextval('rule_id_seq');
        
        -- Set sequence ownership
        ALTER SEQUENCE fixture_id_seq OWNED BY fixture.id;
        ALTER SEQUENCE cup_match_id_seq OWNED BY cup_match.id;
        ALTER SEQUENCE cup_group_id_seq OWNED BY cup_group.id;
        ALTER SEQUENCE cup_group_team_id_seq OWNED BY cup_group_team.id;
        ALTER SEQUENCE cup_group_match_id_seq OWNED BY cup_group_match.id;
        ALTER SEQUENCE rule_id_seq OWNED BY rule.id;
    END $$;
    """)

def downgrade():
    # Drop sequences
    op.execute("""
    DROP SEQUENCE IF EXISTS fixture_id_seq CASCADE;
    DROP SEQUENCE IF EXISTS cup_match_id_seq CASCADE;
    DROP SEQUENCE IF EXISTS cup_group_id_seq CASCADE;
    DROP SEQUENCE IF EXISTS cup_group_team_id_seq CASCADE;
    DROP SEQUENCE IF EXISTS cup_group_match_id_seq CASCADE;
    DROP SEQUENCE IF EXISTS rule_id_seq CASCADE;
    """)