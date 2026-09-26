"""add public token and external candidature fields

Revision ID: 7773f59878be
Revises: 825fe45a3ac7
Create Date: 2026-09-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7773f59878be'
down_revision: Union[str, None] = '825fe45a3ac7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add public_token column to offre table
    op.add_column('offre', sa.Column('public_token', sa.String(), nullable=True, unique=True, index=True))
    
    # Modify candidature table to add external candidate fields and make id_candidat nullable
    op.alter_column('candidature', 'id_candidat', nullable=True)
    op.add_column('candidature', sa.Column('nom_prenom', sa.String(length=255), nullable=True))
    op.add_column('candidature', sa.Column('email', sa.String(length=255), nullable=True))
    op.add_column('candidature', sa.Column('telephone', sa.String(length=50), nullable=True))


def downgrade() -> None:
    # Remove columns from candidature
    op.drop_column('candidature', 'telephone')
    op.drop_column('candidature', 'email')
    op.drop_column('candidature', 'nom_prenom')
    
    # Revert id_candidat to non-nullable
    op.alter_column('candidature', 'id_candidat', nullable=False)
    
    # Remove public_token from offre
    op.drop_column('offre', 'public_token')
