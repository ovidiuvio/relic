"""Add storage tier to relic

Revision ID: 8e2f4a5b6c7d
Revises: 7df3a938dd0d
Create Date: 2025-05-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e2f4a5b6c7d'
down_revision: Union[str, Sequence[str], None] = '7df3a938dd0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('relic', sa.Column('tier', sa.String(), server_default='standard', nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('relic', 'tier')
