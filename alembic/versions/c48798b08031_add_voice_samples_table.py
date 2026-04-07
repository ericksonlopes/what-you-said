"""drop voice_samples table and rename audio_source to audios_path

Revision ID: c48798b08031
Revises: a1b2c3d4e5f6
Create Date: 2026-04-04 15:03:51.624778

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c48798b08031"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop voice_samples table and replace audio_source with audios_path on voices."""
    # Drop voice_samples table (no longer needed - samples are listed from S3)
    op.execute("DROP INDEX IF EXISTS ix_voice_samples_voice_id")
    op.execute("DROP TABLE IF EXISTS voice_samples")

    # Rename audio_source -> audios_path on voices table
    with op.batch_alter_table("voices", schema=None) as batch_op:
        batch_op.add_column(sa.Column("audios_path", sa.String(), nullable=True))

    # Migrate data: convert audio_source (single file path) to directory path
    op.execute("""
        UPDATE voices
        SET audios_path = 'voices/' || id || '/'
        WHERE audios_path IS NULL
    """)

    with op.batch_alter_table("voices", schema=None) as batch_op:
        batch_op.drop_column("audio_source")


def downgrade() -> None:
    """Restore audio_source on voices and recreate voice_samples table."""
    with op.batch_alter_table("voices", schema=None) as batch_op:
        batch_op.add_column(sa.Column("audio_source", sa.String(), nullable=True))

    # Best-effort restore: use first file in audios_path as audio_source
    op.execute("""
        UPDATE voices
        SET audio_source = audios_path || 'reference_' || id || '.wav'
        WHERE audio_source IS NULL AND audios_path IS NOT NULL
    """)

    with op.batch_alter_table("voices", schema=None) as batch_op:
        batch_op.drop_column("audios_path")

    # Recreate voice_samples table
    op.create_table(
        "voice_samples",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("voice_id", sa.String(), nullable=True),
        sa.Column("audio_source", sa.String(), nullable=True),
        sa.Column("duration", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["voice_id"], ["voices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("voice_samples", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_voice_samples_voice_id"), ["voice_id"], unique=False
        )
