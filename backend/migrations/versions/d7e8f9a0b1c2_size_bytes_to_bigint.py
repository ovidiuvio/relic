"""widen relic.size_bytes to BIGINT

Revision ID: d7e8f9a0b1c2
Revises: b4c5d6e7f8a9
Create Date: 2026-07-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd7e8f9a0b1c2'
down_revision: Union[str, Sequence[str], None] = 'b4c5d6e7f8a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _size_bytes_type() -> str:
    """Return the current DB type name of relic.size_bytes."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    for col in inspector.get_columns('relic'):
        if col['name'] == 'size_bytes':
            return str(col['type']).upper()
    return ''


def upgrade() -> None:
    """Widen relic.size_bytes from INTEGER to BIGINT so files over ~2.1 GB can be stored."""
    current = _size_bytes_type()
    if 'BIGINT' in current:
        print("Alembic Skip: relic.size_bytes is already BIGINT")
        return
    op.alter_column('relic', 'size_bytes',
                    existing_type=sa.Integer(),
                    type_=sa.BigInteger())


def downgrade() -> None:
    """Revert relic.size_bytes back to INTEGER (values over 2^31-1 will fail)."""
    current = _size_bytes_type()
    if 'BIGINT' not in current:
        print("Alembic Skip: relic.size_bytes is not BIGINT")
        return
    op.alter_column('relic', 'size_bytes',
                    existing_type=sa.BigInteger(),
                    type_=sa.Integer())
