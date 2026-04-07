"""add vector_store_type to job and chunk index

Revision ID: 5736075a22d0
Revises: 5ff7984a3bcc
Create Date: 2026-03-17 16:58:26.102035

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5736075a22d0"
down_revision: Union[str, Sequence[str], None] = "5ff7984a3bcc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # chunk_index
    columns_chunk = [c["name"] for c in insp.get_columns("chunk_index")]
    if "vector_store_type" not in columns_chunk:
        with op.batch_alter_table("chunk_index", schema=None) as batch_op:
            batch_op.add_column(sa.Column("vector_store_type", sa.Text(), nullable=True))

    # ingestion_jobs
    columns_jobs = [c["name"] for c in insp.get_columns("ingestion_jobs")]
    if "vector_store_type" not in columns_jobs:
        with op.batch_alter_table("ingestion_jobs", schema=None) as batch_op:
            batch_op.add_column(sa.Column("vector_store_type", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    insp = sa.inspect(bind)

    columns_jobs = [c["name"] for c in insp.get_columns("ingestion_jobs")]
    if "vector_store_type" in columns_jobs:
        with op.batch_alter_table("ingestion_jobs", schema=None) as batch_op:
            batch_op.drop_column("vector_store_type")

    columns_chunk = [c["name"] for c in insp.get_columns("chunk_index")]
    if "vector_store_type" in columns_chunk:
        with op.batch_alter_table("chunk_index", schema=None) as batch_op:
            batch_op.drop_column("vector_store_type")
