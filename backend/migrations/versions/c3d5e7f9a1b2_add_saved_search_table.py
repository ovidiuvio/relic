"""add saved_search table

Revision ID: c3d5e7f9a1b2
Revises: f4a8c2e91b7d
Create Date: 2026-09-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c3d5e7f9a1b2'
down_revision: Union[str, Sequence[str], None] = 'f4a8c2e91b7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create saved_search: searches users pinned from the search bar."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'saved_search' in inspector.get_table_names():
        print("Alembic Skip: Table 'saved_search' already exists")
        return
    op.create_table(
        'saved_search',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(32), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=True),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('path', sa.String(1000), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('user_id', 'path', name='unique_user_saved_search_path'),
    )
    op.create_index(op.f('ix_saved_search_user_id'), 'saved_search', ['user_id'])


def downgrade() -> None:
    """Drop saved_search."""
    op.drop_index(op.f('ix_saved_search_user_id'), table_name='saved_search')
    op.drop_table('saved_search')
