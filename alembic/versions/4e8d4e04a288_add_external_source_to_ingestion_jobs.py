"""add external_source to ingestion_jobs

Revision ID: 4e8d4e04a288
Revises: 40f70fb7bb1c
Create Date: 2026-03-19 02:19:07.241910

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4e8d4e04a288"
down_revision: Union[str, Sequence[str], None] = "40f70fb7bb1c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "ingestion_jobs", sa.Column("external_source", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("ingestion_jobs", "external_source")
