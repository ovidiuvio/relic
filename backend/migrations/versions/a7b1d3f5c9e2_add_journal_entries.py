"""add journal entries

Revision ID: a7b1d3f5c9e2
Revises: c3d5e7f9a1b2
Create Date: 2026-09-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a7b1d3f5c9e2'
down_revision: Union[str, Sequence[str], None] = 'c3d5e7f9a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables() -> set:
    """Names of the tables that exist now (init_db() may already have created the new ones)."""
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    """Create journal_entry and journal_entry_tag, the metadata behind journal relics."""
    tables = _tables()
    if 'journal_entry' in tables:
        print("Alembic Skip: table 'journal_entry' already exists")
    else:
        op.create_table(
            'journal_entry',
            sa.Column('id', sa.String(length=32), primary_key=True),
            sa.Column('relic_id', sa.String(length=32), sa.ForeignKey('relic.id', ondelete='CASCADE'), nullable=False),
            sa.Column('path', sa.String(), nullable=False),
            sa.Column('title', sa.String(), nullable=False),
            sa.Column('entry_date', sa.Date(), nullable=False),
            sa.Column('daily', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('pinned', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('excerpt', sa.String(), nullable=False, server_default=''),
            sa.Column('search_text', sa.Text(), nullable=False, server_default=''),
            sa.Column('word_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
            sa.Column('open_tasks', sa.Integer(), nullable=False, server_default=sa.text('0')),
            sa.Column('total_tasks', sa.Integer(), nullable=False, server_default=sa.text('0')),
            sa.Column('size_bytes', sa.Integer(), nullable=False, server_default=sa.text('0')),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.UniqueConstraint('relic_id', 'path', name='uq_journal_entry_relic_path'),
        )
        op.create_index('ix_journal_entry_relic_id', 'journal_entry', ['relic_id'])
        op.create_index('ix_journal_entry_created_at', 'journal_entry', ['created_at'])
        op.create_index('ix_journal_entry_relic_date', 'journal_entry', ['relic_id', 'entry_date'])
    if 'journal_entry_tag' in tables:
        print("Alembic Skip: table 'journal_entry_tag' already exists")
    else:
        op.create_table(
            'journal_entry_tag',
            sa.Column('entry_id', sa.String(length=32), sa.ForeignKey('journal_entry.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('name', sa.String(), primary_key=True),
        )
        op.create_index('ix_journal_entry_tag_name', 'journal_entry_tag', ['name'])


def downgrade() -> None:
    """Drop the journal tables. Entry files stay in storage until their journal relic is deleted."""
    tables = _tables()
    if 'journal_entry_tag' in tables:
        op.drop_table('journal_entry_tag')
    else:
        print("Alembic Skip: table 'journal_entry_tag' does not exist")
    if 'journal_entry' in tables:
        op.drop_table('journal_entry')
    else:
        print("Alembic Skip: table 'journal_entry' does not exist")
