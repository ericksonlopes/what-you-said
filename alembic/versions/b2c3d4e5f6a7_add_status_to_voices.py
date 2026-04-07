"""add status and status_message to voices

Revision ID: b2c3d4e5f6a7
Revises: 04e0f5f5f0af
Create Date: 2026-04-07 15:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "04e0f5f5f0af"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("voices", schema=None) as batch_op:
        batch_op.add_column(sa.Column("status", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("status_message", sa.String(), nullable=True))

    # Backfill: any existing voice row is assumed ready.
    op.execute("UPDATE voices SET status = 'ready' WHERE status IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("voices", schema=None) as batch_op:
        batch_op.drop_column("status_message")
        batch_op.drop_column("status")
