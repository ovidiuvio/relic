"""add client public_id

Revision ID: 556bd97b2ada
Revises: a39d38011b9d
Create Date: 2026-03-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '556bd97b2ada'
down_revision: Union[str, Sequence[str], None] = 'a39d38011b9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add public_id column to client_key and backfill existing rows."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('client_key')]

    if 'public_id' not in columns:
        op.add_column('client_key',
            sa.Column('public_id', sa.String(16), nullable=True)
        )

        # Backfill all existing clients with unique public_ids
        import secrets as _secrets
        result = conn.execute(sa.text("SELECT id FROM client_key WHERE public_id IS NULL"))
        existing_client_ids = [row[0] for row in result.fetchall()]
        used = set()
        for cid in existing_client_ids:
            pid = None
            for _ in range(10):
                candidate = _secrets.token_hex(8)
                if candidate not in used:
                    pid = candidate
                    used.add(pid)
                    break
            if pid:
                conn.execute(
                    sa.text("UPDATE client_key SET public_id = :pid WHERE id = :cid"),
                    {"pid": pid, "cid": cid}
                )

        op.create_index(op.f('ix_client_key_public_id'), 'client_key', ['public_id'], unique=True)
    else:
        print("Alembic Skip: Column 'public_id' already exists on 'client_key'")


def downgrade() -> None:
    """Remove public_id column from client_key."""
    op.drop_index(op.f('ix_client_key_public_id'), table_name='client_key')
    op.drop_column('client_key', 'public_id')
