"""Ajout consentement_banque_profils et date_suppression

Revision ID: c7f8a1b2d3e4
Revises: b89927597392
Create Date: 2026-09-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7f8a1b2d3e4'
down_revision: Union[str, None] = 'b89927597392'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ajouter la colonne consentement_banque_profils à la table candidat
    op.add_column('candidat', sa.Column('consentement_banque_profils', sa.Boolean(), nullable=False, server_default='false'))
    
    # Ajouter la colonne date_suppression à la table offre
    op.add_column('offre', sa.Column('date_suppression', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Supprimer les colonnes ajoutées
    op.drop_column('offre', 'date_suppression')
    op.drop_column('candidat', 'consentement_banque_profils')
