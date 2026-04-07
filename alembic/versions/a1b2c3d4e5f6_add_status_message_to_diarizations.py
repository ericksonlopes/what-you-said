"""add status_message to diarizations

Revision ID: a1b2c3d4e5f6
Revises: d6d36d89a425
Create Date: 2026-04-04 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "d6d36d89a425"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("diarizations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("status_message", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("diarizations", schema=None) as batch_op:
        batch_op.drop_column("status_message")
