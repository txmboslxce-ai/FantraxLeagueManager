"""Add autoincrement to fixture id

Revision ID: add_fixture_autoincrement
Revises: add_sequences
Create Date: 2025-10-12 17:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_fixture_autoincrement'
down_revision = 'add_sequences'
branch_labels = None
depends_on = None

def upgrade():
    # Drop the old primary key constraint
    op.execute('ALTER TABLE fixture DROP CONSTRAINT fixture_pkey;')
    
    # Modify the id column to be a serial
    op.execute('ALTER TABLE fixture ALTER COLUMN id DROP DEFAULT;')
    op.execute('ALTER TABLE fixture ALTER COLUMN id SET DATA TYPE SERIAL;')
    
    # Add back the primary key constraint
    op.execute('ALTER TABLE fixture ADD PRIMARY KEY (id);')

def downgrade():
    # Drop the primary key constraint
    op.execute('ALTER TABLE fixture DROP CONSTRAINT fixture_pkey;')
    
    # Convert back to regular integer
    op.execute('ALTER TABLE fixture ALTER COLUMN id TYPE INTEGER;')
    
    # Add back the primary key constraint
    op.execute('ALTER TABLE fixture ADD PRIMARY KEY (id);')