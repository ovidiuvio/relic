"""add is_admin flag to client_key

Revision ID: e2c9a1f4b7d3
Revises: d7e8f9a0b1c2
Create Date: 2026-07-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e2c9a1f4b7d3'
down_revision: Union[str, Sequence[str], None] = 'd7e8f9a0b1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_is_admin() -> bool:
    """Return True if client_key.is_admin already exists."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return any(col['name'] == 'is_admin' for col in inspector.get_columns('client_key'))


def upgrade() -> None:
    """Add client_key.is_admin so admins can be granted/revoked at runtime without a restart."""
    if _has_is_admin():
        print("Alembic Skip: client_key.is_admin already exists")
        return
    op.add_column(
        'client_key',
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )
    op.create_index(op.f('ix_client_key_is_admin'), 'client_key', ['is_admin'])


def downgrade() -> None:
    """Drop client_key.is_admin, reverting to env-only (ADMIN_CLIENT_IDS) admin definitions."""
    if not _has_is_admin():
        print("Alembic Skip: client_key.is_admin does not exist")
        return
    op.drop_index(op.f('ix_client_key_is_admin'), table_name='client_key')
    op.drop_column('client_key', 'is_admin')
