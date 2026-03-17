"""add vector_store_type to job and chunk index

Revision ID: 5736075a22d0
Revises: 5ff7984a3bcc
Create Date: 2026-03-17 16:58:26.102035

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5736075a22d0'
down_revision: Union[str, Sequence[str], None] = '5ff7984a3bcc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('chunk_index', sa.Column('vector_store_type', sa.Text(), nullable=True))
    op.add_column('ingestion_jobs', sa.Column('vector_store_type', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('ingestion_jobs', 'vector_store_type')
    op.drop_column('chunk_index', 'vector_store_type')
