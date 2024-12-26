"""Add rent column to Vehicle table

Revision ID: ad580ed717d9
Revises: 
Create Date: 2024-12-26 09:40:31.123456

"""
from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = 'ad580ed717d9'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add the 'rent' column with a default value of 0
    with op.batch_alter_table('vehicle', schema=None) as batch_op:
        batch_op.add_column(sa.Column('rent', sa.Integer(), nullable=False, server_default='0'))

    # Remove the server default
    with op.batch_alter_table('vehicle', schema=None) as batch_op:
        batch_op.alter_column('rent', server_default=None)

def downgrade():
    with op.batch_alter_table('vehicle', schema=None) as batch_op:
        batch_op.drop_column('rent')