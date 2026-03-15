"""add username to users

Revision ID: 3d9f8a1b7c2e
Revises: 947b15f79c58
Create Date: 2026-03-15 00:00:00.000000

"""
from typing import Sequence, Union
import re

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3d9f8a1b7c2e'
down_revision: Union[str, Sequence[str], None] = '947b15f79c58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _normalize_username(seed: str) -> str:
    candidate = re.sub(r'[^A-Za-z0-9]', '', seed or '').lower()
    if not candidate:
        candidate = 'user'
    if not any(ch.isalpha() for ch in candidate):
        candidate = f'user{candidate}'
    return candidate[:32]


def upgrade() -> None:
    op.add_column('users', sa.Column('username', sa.String(length=32), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.text('SELECT id, email FROM users ORDER BY id ASC')).fetchall()

    used: set[str] = set()
    for row in rows:
        user_id = int(row[0])
        email = str(row[1] or '')
        base_seed = email.split('@')[0] if '@' in email else email
        base = _normalize_username(base_seed)

        username = base
        suffix = 1
        while username in used:
            tail = str(suffix)
            username = f"{base[:32-len(tail)]}{tail}"
            suffix += 1

        used.add(username)
        bind.execute(
            sa.text('UPDATE users SET username = :username WHERE id = :id'),
            {'username': username, 'id': user_id},
        )

    op.create_index('ix_users_username', 'users', ['username'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_users_username', table_name='users')
    op.drop_column('users', 'username')
