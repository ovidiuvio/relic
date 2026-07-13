"""add api_metrics table for cross-worker API metrics aggregation

Revision ID: e8a1c4d7f2b5
Revises: d7e8f9a0b1c2
Create Date: 2026-07-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = 'e8a1c4d7f2b5'
down_revision: Union[str, Sequence[str], None] = 'd7e8f9a0b1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists() -> bool:
    conn = op.get_bind()
    return sa.inspect(conn).has_table('api_metrics')


def upgrade() -> None:
    """Create the api_metrics table: one row per 10s bucket per worker process,
    holding request/error counts, latency and DB timing sums, per-route JSONB
    breakdowns, and slow-query samples for the admin Monitor tab."""
    if _table_exists():
        print("Alembic Skip: api_metrics table already exists")
        return
    op.create_table(
        'api_metrics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('bucket_ts', sa.DateTime(), nullable=False),
        sa.Column('worker_pid', sa.Integer(), nullable=False),
        sa.Column('requests', sa.Integer(), nullable=False),
        sa.Column('errors', sa.Integer(), nullable=False),
        sa.Column('client_errors', sa.Integer(), nullable=False),
        sa.Column('total_ms', sa.Float(), nullable=False),
        sa.Column('max_ms', sa.Float(), nullable=False),
        sa.Column('db_ms', sa.Float(), nullable=False),
        sa.Column('db_queries', sa.Integer(), nullable=False),
        sa.Column('routes', JSONB(), nullable=True),
        sa.Column('slow_queries', JSONB(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_api_metrics_bucket_ts', 'api_metrics', ['bucket_ts'])


def downgrade() -> None:
    """Drop the api_metrics table and its bucket_ts index."""
    if not _table_exists():
        print("Alembic Skip: api_metrics table does not exist")
        return
    op.drop_index('ix_api_metrics_bucket_ts', table_name='api_metrics')
    op.drop_table('api_metrics')
