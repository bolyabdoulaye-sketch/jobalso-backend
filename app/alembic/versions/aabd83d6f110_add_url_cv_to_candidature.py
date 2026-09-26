"""add url_cv to candidature

Revision ID: aabd83d6f110
Revises: 7773f59878be
Create Date: 2026-09-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'aabd83d6f110'
down_revision: Union[str, None] = '7773f59878be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add url_cv column to candidature table for external candidates
    op.add_column('candidature', sa.Column('url_cv', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove url_cv column
    op.drop_column('candidature', 'url_cv')
