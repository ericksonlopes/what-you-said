"""add_content_source_id_to_duplicates

Revision ID: 84524e052673
Revises: 646a175ac845
Create Date: 2026-04-08 10:50:39.027257

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '84524e052673'
down_revision: Union[str, Sequence[str], None] = '646a175ac845'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('chunk_duplicates', schema=None) as batch_op:
        batch_op.add_column(sa.Column('content_source_id', sa.UUID(), nullable=True))
        batch_op.create_foreign_key('fk_chunk_duplicates_content_source_id_content_sources', 'content_sources', ['content_source_id'], ['id'], initially='IMMEDIATE', deferrable=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('chunk_duplicates', schema=None) as batch_op:
        batch_op.drop_constraint('fk_chunk_duplicates_content_source_id_content_sources', type_='foreignkey')
        batch_op.drop_column('content_source_id')
