"""initial schema

Revision ID: 947b15f79c58
Revises: 
Create Date: 2026-03-13 23:17:18.939946

"""
from typing import Sequence, Union

from alembic import op

from app.db.base import Base


# revision identifiers, used by Alembic.
revision: str = '947b15f79c58'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
