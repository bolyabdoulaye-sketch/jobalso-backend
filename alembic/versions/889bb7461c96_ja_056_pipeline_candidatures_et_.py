"""JA-056 pipeline candidatures et historique

Revision ID: 889bb7461c96
Revises: 7ef701dd6a7d
Create Date: 2026-09-24 10:03:54.560186

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '889bb7461c96'
down_revision: Union[str, Sequence[str], None] = '7ef701dd6a7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Anciennes valeurs libres -> premier statut du pipeline
    op.execute("UPDATE resultat SET statut_candidature = 'RECUE' WHERE statut_candidature = 'en_attente'")

    op.create_table('historique_statut_candidature',
    sa.Column('id_historique', sa.Uuid(), nullable=False),
    sa.Column('id_resultat', sa.Uuid(), nullable=False),
    sa.Column('ancien_statut', sa.String(length=50), nullable=True),
    sa.Column('nouveau_statut', sa.String(length=50), nullable=False),
    sa.Column('id_utilisateur', sa.Uuid(), nullable=False),
    sa.Column('date_changement', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['id_resultat'], ['resultat.id_resultat'], ),
    sa.ForeignKeyConstraint(['id_utilisateur'], ['utilisateur.id_utilisateur'], ),
    sa.PrimaryKeyConstraint('id_historique')
    )
    op.create_index(op.f('ix_historique_statut_candidature_id_resultat'), 'historique_statut_candidature', ['id_resultat'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_historique_statut_candidature_id_resultat'), table_name='historique_statut_candidature')
    op.drop_table('historique_statut_candidature')
    op.execute("UPDATE resultat SET statut_candidature = 'en_attente' WHERE statut_candidature = 'RECUE'")