"""add source_metadata to diarizations

Revision ID: d6d36d89a425
Revises: 4c007a7c27e8
Create Date: 2026-04-04 00:53:09.873020

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d6d36d89a425"
down_revision: Union[str, Sequence[str], None] = "4c007a7c27e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("diarizations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("source_metadata", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("diarizations", schema=None) as batch_op:
        batch_op.drop_column("source_metadata")
