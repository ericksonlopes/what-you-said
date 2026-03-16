"""add status_message to ingestion_jobs

Revision ID: 31fc75e62cf8
Revises: 1062951c28c7
Create Date: 2026-03-15 02:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '31fc75e62cf8'
down_revision: Union[str, None] = 'a4e3eb3d951c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table('ingestion_jobs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status_message', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('current_step', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('total_steps', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('ingestion_jobs', schema=None) as batch_op:
        batch_op.drop_column('total_steps')
        batch_op.drop_column('current_step')
        batch_op.drop_column('status_message')
