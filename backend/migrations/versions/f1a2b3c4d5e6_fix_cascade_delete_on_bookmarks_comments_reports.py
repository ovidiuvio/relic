"""fix cascade delete on bookmarks, comments, and reports

Adds ON DELETE CASCADE to the relic_id foreign keys on client_bookmark,
comment, and relic_report so that deleting a relic no longer raises an
IntegrityError when child rows exist.

Revision ID: f1a2b3c4d5e6
Revises: c3f8e2b1a4d9
Create Date: 2026-03-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'c3f8e2b1a4d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table, column, old_constraint_name, new_constraint_name, ref_table)
_TARGETS = [
    ('client_bookmark', 'relic_id', 'client_bookmark_relic_id_fkey', 'client_bookmark_relic_id_fkey', 'relic'),
    ('comment',         'relic_id', 'comment_relic_id_fkey',         'comment_relic_id_fkey',         'relic'),
    ('relic_report',    'relic_id', 'relic_report_relic_id_fkey',    'relic_report_relic_id_fkey',    'relic'),
]


def _existing_fk_names(conn, table: str) -> set:
    inspector = sa.inspect(conn)
    return {fk['name'] for fk in inspector.get_foreign_keys(table)}


def upgrade() -> None:
    """Replace relic_id FK constraints with ON DELETE CASCADE variants."""
    conn = op.get_bind()

    for table, column, old_name, new_name, ref_table in _TARGETS:
        existing = _existing_fk_names(conn, table)

        if old_name in existing:
            op.drop_constraint(old_name, table, type_='foreignkey')
        else:
            print(f"Alembic Skip: constraint '{old_name}' not found on '{table}', skipping drop")

        if new_name not in _existing_fk_names(conn, table):
            op.create_foreign_key(
                new_name, table, ref_table,
                [column], ['id'],
                ondelete='CASCADE',
            )
        else:
            print(f"Alembic Skip: constraint '{new_name}' already exists on '{table}'")


def downgrade() -> None:
    """Restore relic_id FK constraints without ON DELETE CASCADE."""
    conn = op.get_bind()

    for table, column, old_name, new_name, ref_table in _TARGETS:
        existing = _existing_fk_names(conn, table)

        if new_name in existing:
            op.drop_constraint(new_name, table, type_='foreignkey')
        else:
            print(f"Alembic Skip: constraint '{new_name}' not found on '{table}', skipping drop")

        if old_name not in _existing_fk_names(conn, table):
            op.create_foreign_key(
                old_name, table, ref_table,
                [column], ['id'],
            )
        else:
            print(f"Alembic Skip: constraint '{old_name}' already exists on '{table}'")
