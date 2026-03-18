"""Update unique constraint on content_sources to include subject_id

Revision ID: 0ce7f69147eb
Revises: 5736075a22d0
Create Date: 2026-03-18 12:27:04.170085

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0ce7f69147eb"
down_revision: Union[str, Sequence[str], None] = "5736075a22d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Using batch mode for SQLite compatibility
    with op.batch_alter_table("content_sources", schema=None) as batch_op:
        batch_op.drop_constraint(
            op.f("uq_content_source_external_source"), type_="unique"
        )
        batch_op.create_unique_constraint(
            "uq_content_source_external_source_per_subject",
            ["external_source", "subject_id"],
        )

    with op.batch_alter_table("ingestion_jobs", schema=None) as batch_op:
        batch_op.alter_column(
            "status_message",
            existing_type=sa.VARCHAR(),
            type_=sa.Text(),
            existing_nullable=True,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("ingestion_jobs", schema=None) as batch_op:
        batch_op.alter_column(
            "status_message",
            existing_type=sa.Text(),
            type_=sa.VARCHAR(),
            existing_nullable=True,
        )

    with op.batch_alter_table("content_sources", schema=None) as batch_op:
        batch_op.drop_constraint(
            "uq_content_source_external_source_per_subject",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            op.f("uq_content_source_external_source"),
            ["external_source"],
        )
