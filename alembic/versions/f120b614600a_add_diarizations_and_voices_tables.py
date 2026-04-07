"""add diarizations and voices tables

Revision ID: f120b614600a
Revises: c16fab000f02
Create Date: 2026-04-02 22:12:24.017538

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f120b614600a"
down_revision: Union[str, Sequence[str], None] = "c16fab000f02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "diarizations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("source_type", sa.String(), nullable=True),
        sa.Column("external_source", sa.String(), nullable=True),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("folder_path", sa.String(), nullable=True),
        sa.Column("storage_path", sa.String(), nullable=True),
        sa.Column("segments", sa.JSON(), nullable=True),
        sa.Column("recognition_results", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    with op.batch_alter_table("diarizations", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_diarizations_title"),
            ["title"],
            unique=False,
            if_not_exists=True,
        )

    op.create_table(
        "voices",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("audio_source", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    with op.batch_alter_table("voices", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_voices_name"), ["name"], unique=True, if_not_exists=True
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("voices", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_voices_name"), if_exists=True)

    op.drop_table("voices", if_exists=True)
    with op.batch_alter_table("diarizations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_diarizations_title"), if_exists=True)

    op.drop_table("diarizations", if_exists=True)
