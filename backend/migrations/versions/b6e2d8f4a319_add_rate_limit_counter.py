"""add rate_limit_counter table

Revision ID: b6e2d8f4a319
Revises: a5d1c7e3f204
Create Date: 2026-07-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b6e2d8f4a319'
down_revision: Union[str, Sequence[str], None] = 'a5d1c7e3f204'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


EXPIRY_INDEX = 'ix_rate_limit_counter_expires_at'


def _has_table(name: str) -> bool:
    """Return True if the table already exists."""
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    """Add shared rate-limit counters. The backend runs several gunicorn
    workers, so counters must live outside any single process to be accurate."""
    if _has_table('rate_limit_counter'):
        print("Alembic Skip: table 'rate_limit_counter' already exists")
        return

    op.create_table(
        'rate_limit_counter',
        sa.Column('key', sa.String(200), primary_key=True),
        sa.Column('count', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
    )
    op.create_index(EXPIRY_INDEX, 'rate_limit_counter', ['expires_at'])


def downgrade() -> None:
    """Drop shared rate-limit counters, leaving no rate limiting at all."""
    if not _has_table('rate_limit_counter'):
        print("Alembic Skip: table 'rate_limit_counter' does not exist")
        return

    op.drop_index(EXPIRY_INDEX, table_name='rate_limit_counter')
    op.drop_table('rate_limit_counter')
