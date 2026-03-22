"""add cascade delete to relic_tags

Adds ON DELETE CASCADE to both foreign keys on the relic_tags association
table so that deleting a relic or tag does not raise an IntegrityError
when child rows exist (e.g. via bulk SQL delete or admin raw query).

Revision ID: b4c5d6e7f8a9
Revises: f1a2b3c4d5e6
Create Date: 2026-03-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b4c5d6e7f8a9'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table, column, constraint_name, referenced_table)
_TARGETS = [
    ('relic_tags', 'relic_id', 'relic_tags_relic_id_fkey', 'relic'),
    ('relic_tags', 'tag_id',   'relic_tags_tag_id_fkey',   'tag'),
]


def _existing_fk_names(conn, table: str) -> set:
    inspector = sa.inspect(conn)
    return {fk['name'] for fk in inspector.get_foreign_keys(table)}


def upgrade() -> None:
    """Replace relic_tags FK constraints with ON DELETE CASCADE variants."""
    conn = op.get_bind()

    for table, column, fk_name, ref_table in _TARGETS:
        existing = _existing_fk_names(conn, table)

        if fk_name in existing:
            op.drop_constraint(fk_name, table, type_='foreignkey')
        else:
            print(f"Alembic Skip: constraint '{fk_name}' not found on '{table}', skipping drop")

        if fk_name not in _existing_fk_names(conn, table):
            op.create_foreign_key(
                fk_name, table, ref_table,
                [column], ['id'],
                ondelete='CASCADE',
            )
        else:
            print(f"Alembic Skip: constraint '{fk_name}' already exists on '{table}'")


def downgrade() -> None:
    """Restore relic_tags FK constraints without ON DELETE CASCADE."""
    conn = op.get_bind()

    for table, column, fk_name, ref_table in _TARGETS:
        existing = _existing_fk_names(conn, table)

        if fk_name in existing:
            op.drop_constraint(fk_name, table, type_='foreignkey')
        else:
            print(f"Alembic Skip: constraint '{fk_name}' not found on '{table}', skipping drop")

        if fk_name not in _existing_fk_names(conn, table):
            op.create_foreign_key(
                fk_name, table, ref_table,
                [column], ['id'],
            )
        else:
            print(f"Alembic Skip: constraint '{fk_name}' already exists on '{table}'")
