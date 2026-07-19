"""rename client to user

Revision ID: f4a8c2e91b7d
Revises: e2c9a1f4b7d3
Create Date: 2026-07-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f4a8c2e91b7d'
down_revision: Union[str, Sequence[str], None] = 'e2c9a1f4b7d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _rename_table(conn, inspector, old: str, new: str) -> None:
    """Rename a table, guarding against Base.metadata.create_all() having
    already created an empty `new` table (init_db() runs create_all() before
    migrations, and models.py now declares the new name)."""
    tables = inspector.get_table_names()
    if old not in tables:
        print(f"Alembic Skip: table '{old}' not found (already renamed or fresh install)")
        return
    if new in tables:
        count = conn.execute(sa.text(f'SELECT COUNT(*) FROM "{new}"')).scalar()
        if count:
            raise RuntimeError(
                f"Refusing to rename '{old}' -> '{new}': '{new}' already exists and is not empty"
            )
        # CASCADE: create_all() may have created other fresh (also-empty) tables
        # with FKs pointing at this one (e.g. user_bookmark -> users) before this
        # migration ran; those tables get dropped-and-recreated-by-rename in their
        # own turn, so losing their FK constraint here is harmless.
        conn.execute(sa.text(f'DROP TABLE "{new}" CASCADE'))
    op.rename_table(old, new)


def _rename_column(inspector, table: str, old_col: str, new_col: str) -> None:
    columns = [c['name'] for c in inspector.get_columns(table)]
    if old_col in columns and new_col not in columns:
        op.alter_column(table, old_col, new_column_name=new_col)
    elif new_col in columns:
        print(f"Alembic Skip: column '{new_col}' already exists on '{table}'")
    else:
        print(f"Alembic Skip: column '{old_col}' not found on '{table}'")


def _rename_index(conn, inspector, table: str, old_name: str, new_name: str) -> None:
    indexes = [i['name'] for i in inspector.get_indexes(table)]
    if old_name in indexes:
        conn.execute(sa.text(f'ALTER INDEX "{old_name}" RENAME TO "{new_name}"'))
    else:
        print(f"Alembic Skip: index '{old_name}' not found on '{table}'")


def _rename_unique_constraint(conn, inspector, table: str, old_name: str, new_name: str) -> None:
    constraints = [c['name'] for c in inspector.get_unique_constraints(table)]
    if old_name in constraints:
        conn.execute(sa.text(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{old_name}" TO "{new_name}"'))
    else:
        print(f"Alembic Skip: unique constraint '{old_name}' not found on '{table}'")


def upgrade() -> None:
    """Rename the client_key/client_bookmark tables and every client_id/owner_client_id
    column to the user_id/owner_id naming used across the rest of the codebase."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    _rename_table(conn, inspector, 'client_key', 'users')
    inspector = sa.inspect(conn)
    _rename_index(conn, inspector, 'users', 'ix_client_key_public_id', 'ix_users_public_id')
    _rename_index(conn, inspector, 'users', 'ix_client_key_is_admin', 'ix_users_is_admin')

    _rename_table(conn, inspector, 'client_bookmark', 'user_bookmark')
    inspector = sa.inspect(conn)
    _rename_index(conn, inspector, 'user_bookmark', 'ix_client_bookmark_client_id', 'ix_user_bookmark_user_id')
    _rename_index(conn, inspector, 'user_bookmark', 'ix_client_bookmark_relic_id', 'ix_user_bookmark_relic_id')
    _rename_index(conn, inspector, 'user_bookmark', 'ix_client_bookmark_created_at', 'ix_user_bookmark_created_at')
    _rename_unique_constraint(conn, inspector, 'user_bookmark', 'unique_client_relic_bookmark', 'unique_user_relic_bookmark')

    _rename_column(inspector, 'space', 'owner_client_id', 'owner_id')
    inspector = sa.inspect(conn)
    _rename_index(conn, inspector, 'space', 'ix_space_owner_client_id', 'ix_space_owner_id')

    _rename_column(inspector, 'space_access', 'client_id', 'user_id')
    inspector = sa.inspect(conn)
    _rename_index(conn, inspector, 'space_access', 'ix_space_access_client_id', 'ix_space_access_user_id')
    _rename_unique_constraint(conn, inspector, 'space_access', 'unique_space_client_access', 'unique_space_user_access')

    _rename_column(inspector, 'relic', 'client_id', 'user_id')
    inspector = sa.inspect(conn)
    _rename_index(conn, inspector, 'relic', 'ix_relic_client_id', 'ix_relic_user_id')

    _rename_column(inspector, 'relic_access', 'client_id', 'user_id')
    inspector = sa.inspect(conn)
    _rename_index(conn, inspector, 'relic_access', 'ix_relic_access_client_id', 'ix_relic_access_user_id')
    _rename_unique_constraint(conn, inspector, 'relic_access', 'unique_relic_client_access', 'unique_relic_user_access')

    _rename_column(inspector, 'comment', 'client_id', 'user_id')

    _rename_column(inspector, 'user_bookmark', 'client_id', 'user_id')


def downgrade() -> None:
    """Revert the users/user_bookmark tables and user_id/owner_id columns back
    to the original client_key/client_bookmark/client_id naming."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    _rename_column(inspector, 'comment', 'user_id', 'client_id')

    _rename_unique_constraint(conn, inspector, 'relic_access', 'unique_relic_user_access', 'unique_relic_client_access')
    _rename_index(conn, inspector, 'relic_access', 'ix_relic_access_user_id', 'ix_relic_access_client_id')
    _rename_column(inspector, 'relic_access', 'user_id', 'client_id')
    inspector = sa.inspect(conn)

    _rename_index(conn, inspector, 'relic', 'ix_relic_user_id', 'ix_relic_client_id')
    _rename_column(inspector, 'relic', 'user_id', 'client_id')
    inspector = sa.inspect(conn)

    _rename_unique_constraint(conn, inspector, 'space_access', 'unique_space_user_access', 'unique_space_client_access')
    _rename_index(conn, inspector, 'space_access', 'ix_space_access_user_id', 'ix_space_access_client_id')
    _rename_column(inspector, 'space_access', 'user_id', 'client_id')
    inspector = sa.inspect(conn)

    _rename_index(conn, inspector, 'space', 'ix_space_owner_id', 'ix_space_owner_client_id')
    _rename_column(inspector, 'space', 'owner_id', 'owner_client_id')
    inspector = sa.inspect(conn)

    _rename_column(inspector, 'user_bookmark', 'user_id', 'client_id')
    inspector = sa.inspect(conn)
    _rename_unique_constraint(conn, inspector, 'user_bookmark', 'unique_user_relic_bookmark', 'unique_client_relic_bookmark')
    _rename_index(conn, inspector, 'user_bookmark', 'ix_user_bookmark_user_id', 'ix_client_bookmark_client_id')
    _rename_index(conn, inspector, 'user_bookmark', 'ix_user_bookmark_relic_id', 'ix_client_bookmark_relic_id')
    _rename_index(conn, inspector, 'user_bookmark', 'ix_user_bookmark_created_at', 'ix_client_bookmark_created_at')
    _rename_table(conn, inspector, 'user_bookmark', 'client_bookmark')
    inspector = sa.inspect(conn)

    _rename_index(conn, inspector, 'users', 'ix_users_is_admin', 'ix_client_key_is_admin')
    _rename_index(conn, inspector, 'users', 'ix_users_public_id', 'ix_client_key_public_id')
    _rename_table(conn, inspector, 'users', 'client_key')
