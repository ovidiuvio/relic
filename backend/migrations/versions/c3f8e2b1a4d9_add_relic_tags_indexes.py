"""add relic_tags indexes

Revision ID: c3f8e2b1a4d9
Revises: 7e3f9b1c5d2a
Create Date: 2026-03-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c3f8e2b1a4d9'
down_revision: Union[str, Sequence[str], None] = '7e3f9b1c5d2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add indexes on relic_tags(relic_id) and relic_tags(tag_id) to speed up tag joins."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = {idx['name'] for idx in inspector.get_indexes('relic_tags')}

    if 'ix_relic_tags_relic_id' not in existing:
        op.create_index('ix_relic_tags_relic_id', 'relic_tags', ['relic_id'])
    else:
        print("Alembic Skip: Index 'ix_relic_tags_relic_id' already exists")

    if 'ix_relic_tags_tag_id' not in existing:
        op.create_index('ix_relic_tags_tag_id', 'relic_tags', ['tag_id'])
    else:
        print("Alembic Skip: Index 'ix_relic_tags_tag_id' already exists")


def downgrade() -> None:
    """Remove relic_tags indexes."""
    op.drop_index('ix_relic_tags_relic_id', table_name='relic_tags')
    op.drop_index('ix_relic_tags_tag_id', table_name='relic_tags')
