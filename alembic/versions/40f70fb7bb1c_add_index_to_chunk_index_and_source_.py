"""add index to chunk_index and source_title to ingestion_jobs

Revision ID: 40f70fb7bb1c
Revises: 0ce7f69147eb
Create Date: 2026-03-18 23:19:09.848350

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "40f70fb7bb1c"
down_revision: Union[str, Sequence[str], None] = "0ce7f69147eb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # chunk_index
    columns_chunk = [c["name"] for c in insp.get_columns("chunk_index")]
    if "index" not in columns_chunk:
        with op.batch_alter_table("chunk_index", schema=None) as batch_op:
            batch_op.add_column(sa.Column("index", sa.Integer(), nullable=True))

    # ingestion_jobs
    columns_jobs = [c["name"] for c in insp.get_columns("ingestion_jobs")]
    if "source_title" not in columns_jobs:
        with op.batch_alter_table("ingestion_jobs", schema=None) as batch_op:
            batch_op.add_column(sa.Column("source_title", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    insp = sa.inspect(bind)

    columns_jobs = [c["name"] for c in insp.get_columns("ingestion_jobs")]
    if "source_title" in columns_jobs:
        with op.batch_alter_table("ingestion_jobs", schema=None) as batch_op:
            batch_op.drop_column("source_title")

    columns_chunk = [c["name"] for c in insp.get_columns("chunk_index")]
    if "index" in columns_chunk:
        with op.batch_alter_table("chunk_index", schema=None) as batch_op:
            batch_op.drop_column("index")
