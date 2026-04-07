"""add_tokens_count_to_chunks

Revision ID: a4e3eb3d951c
Revises: 1062951c28c7
Create Date: 2026-03-14 15:35:48.848571

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4e3eb3d951c"
down_revision: Union[str, Sequence[str], None] = "1062951c28c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = [c["name"] for c in insp.get_columns("chunk_index")]

    if "tokens_count" not in columns:
        with op.batch_alter_table("chunk_index", schema=None) as batch_op:
            batch_op.add_column(sa.Column("tokens_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = [c["name"] for c in insp.get_columns("chunk_index")]

    if "tokens_count" in columns:
        with op.batch_alter_table("chunk_index", schema=None) as batch_op:
            batch_op.drop_column("tokens_count")
