"""add content column to chunk_index

Revision ID: 790acc587e00
Revises: bd01964d9b26
Create Date: 2026-03-13 22:31:09.706462

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "790acc587e00"
down_revision: Union[str, Sequence[str], None] = "bd01964d9b26"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = [c["name"] for c in insp.get_columns("chunk_index")]

    if "content" not in columns:
        with op.batch_alter_table("chunk_index", schema=None) as batch_op:
            batch_op.add_column(sa.Column("content", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = [c["name"] for c in insp.get_columns("chunk_index")]

    if "content" in columns:
        with op.batch_alter_table("chunk_index", schema=None) as batch_op:
            batch_op.drop_column("content")
