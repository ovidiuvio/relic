"""add site_setting table and per-user quota overrides

Revision ID: a5d1c7e3f204
Revises: f4a8c2e91b7d
Create Date: 2026-07-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a5d1c7e3f204'
down_revision: Union[str, Sequence[str], None] = 'f4a8c2e91b7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


QUOTA_COLUMNS = (
    ('quota_max_relics', sa.Integer),
    ('quota_max_relics_per_day', sa.Integer),
    # BigInteger to match relic.size_bytes; int4 would cap a storage quota at ~2.1 GB
    ('quota_max_storage_bytes', sa.BigInteger),
)

RELIC_USAGE_INDEX = 'ix_relic_user_id_created_at'


def _has_table(name: str) -> bool:
    """Return True if the table already exists."""
    return name in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table: str, column: str) -> bool:
    """Return True if the column already exists on the table."""
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return False
    return any(col['name'] == column for col in inspector.get_columns(table))


def _has_index(table: str, name: str) -> bool:
    """Return True if the index already exists on the table."""
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return False
    return any(idx['name'] == name for idx in inspector.get_indexes(table))


def upgrade() -> None:
    """Add runtime-configurable settings storage and per-user quota overrides,
    so limits can be changed from the admin dashboard without a restart."""
    if _has_table('site_setting'):
        print("Alembic Skip: table 'site_setting' already exists")
    else:
        op.create_table(
            'site_setting',
            sa.Column('key', sa.String(64), primary_key=True),
            sa.Column('value', sa.JSON(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.Column('updated_by', sa.String(32), nullable=True),
        )

    # Nullable with no server default: NULL means "inherit the global default",
    # which is deliberately distinct from 0 ("unlimited").
    for name, column_type in QUOTA_COLUMNS:
        if _has_column('users', name):
            print(f"Alembic Skip: users.{name} already exists")
            continue
        op.add_column('users', sa.Column(name, column_type(), nullable=True))

    if _has_index('relic', RELIC_USAGE_INDEX):
        print(f"Alembic Skip: index '{RELIC_USAGE_INDEX}' already exists")
    else:
        op.create_index(RELIC_USAGE_INDEX, 'relic', ['user_id', 'created_at'])


def downgrade() -> None:
    """Drop runtime settings and quota overrides, reverting to limits that are
    fixed at process start by environment variables."""
    if _has_index('relic', RELIC_USAGE_INDEX):
        op.drop_index(RELIC_USAGE_INDEX, table_name='relic')
    else:
        print(f"Alembic Skip: index '{RELIC_USAGE_INDEX}' does not exist")

    for name, _ in reversed(QUOTA_COLUMNS):
        if _has_column('users', name):
            op.drop_column('users', name)
        else:
            print(f"Alembic Skip: users.{name} does not exist")

    if _has_table('site_setting'):
        op.drop_table('site_setting')
    else:
        print("Alembic Skip: table 'site_setting' does not exist")
