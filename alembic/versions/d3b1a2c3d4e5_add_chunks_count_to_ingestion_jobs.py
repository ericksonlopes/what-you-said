"""add chunks_count to ingestion_jobs

Revision ID: d3b1a2c3d4e5
Revises: 31fc75e62cf8
Create Date: 2026-03-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3b1a2c3d4e5'
down_revision: Union[str, None] = '31fc75e62cf8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table('ingestion_jobs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('chunks_count', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('ingestion_jobs', schema=None) as batch_op:
        batch_op.drop_column('chunks_count')
