"""add_ingestion_type_to_jobs

Revision ID: 1062951c28c7
Revises: 790acc587e00
Create Date: 2026-03-14 15:22:28.848571

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1062951c28c7"
down_revision: Union[str, Sequence[str], None] = "790acc587e00"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = [c["name"] for c in insp.get_columns("ingestion_jobs")]

    if "ingestion_type" not in columns:
        with op.batch_alter_table("ingestion_jobs", schema=None) as batch_op:
            batch_op.add_column(sa.Column("ingestion_type", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = [c["name"] for c in insp.get_columns("ingestion_jobs")]

    if "ingestion_type" in columns:
        with op.batch_alter_table("ingestion_jobs", schema=None) as batch_op:
            batch_op.drop_column("ingestion_type")
