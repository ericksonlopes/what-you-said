"""add index to chunk_index and source_title to ingestion_jobs

Revision ID: 40f70fb7bb1c
Revises: 0ce7f69147eb
Create Date: 2026-03-18 23:19:09.848350

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "40f70fb7bb1c"
down_revision: Union[str, Sequence[str], None] = "0ce7f69147eb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("chunk_index", sa.Column("index", sa.Integer(), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("source_title", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("ingestion_jobs", "source_title")
    op.drop_column("chunk_index", "index")
