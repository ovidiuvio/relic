"""add journal entry links and revisions

Revision ID: b8c2e4f6a1d3
Revises: a7b1d3f5c9e2
Create Date: 2026-09-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b8c2e4f6a1d3'
down_revision: Union[str, Sequence[str], None] = 'a7b1d3f5c9e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables() -> set:
    """Names of the tables that exist now (init_db() may already have created the new ones)."""
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    """Create journal_entry_link (wiki links and embeds) and journal_entry_revision (undo history)."""
    tables = _tables()
    if 'journal_entry_link' in tables:
        print("Alembic Skip: table 'journal_entry_link' already exists")
    else:
        op.create_table(
            'journal_entry_link',
            sa.Column('entry_id', sa.String(length=32), sa.ForeignKey('journal_entry.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('target', sa.String(), primary_key=True),
            sa.Column('label', sa.String(), nullable=False, server_default=''),
            sa.Column('embed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('section', sa.String(), nullable=False, server_default=''),
        )
        op.create_index('ix_journal_entry_link_target', 'journal_entry_link', ['target'])
    if 'journal_entry_revision' in tables:
        print("Alembic Skip: table 'journal_entry_revision' already exists")
    else:
        op.create_table(
            'journal_entry_revision',
            sa.Column('id', sa.String(length=32), primary_key=True),
            sa.Column('entry_id', sa.String(length=32), sa.ForeignKey('journal_entry.id', ondelete='CASCADE'), nullable=False),
            sa.Column('title', sa.String(), nullable=False, server_default=''),
            sa.Column('body', sa.Text(), nullable=False, server_default=''),
            sa.Column('word_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_journal_entry_revision_entry_id', 'journal_entry_revision', ['entry_id'])
        op.create_index('ix_journal_entry_revision_created_at', 'journal_entry_revision', ['created_at'])


def downgrade() -> None:
    """Drop the link and revision tables."""
    tables = _tables()
    for name in ('journal_entry_revision', 'journal_entry_link'):
        if name in tables:
            op.drop_table(name)
        else:
            print(f"Alembic Skip: table '{name}' does not exist")
