"""rename_diarization_title_to_name

Revision ID: 72f69987a221
Revises: 6e53bc32edfe
Create Date: 2026-04-06 10:19:53.966146

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "72f69987a221"
down_revision: Union[str, Sequence[str], None] = "6e53bc32edfe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("diarizations", schema=None) as batch_op:
        batch_op.alter_column(
            "title", new_column_name="name", existing_type=sa.String()
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("diarizations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("title", sa.VARCHAR(), nullable=True))
        batch_op.drop_index(batch_op.f("ix_diarizations_name"), if_exists=True)
        batch_op.create_index(
            batch_op.f("ix_diarizations_title"),
            ["title"],
            unique=False,
            if_not_exists=True,
        )
        batch_op.alter_column(
            "subject_id",
            existing_type=sa.UUID(),
            type_=sa.VARCHAR(),
            existing_nullable=True,
        )
        batch_op.drop_column("name")
