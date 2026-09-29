"""suppression des donnees et du schema entreprise

Revision ID: 4c8e7a91d2f0
Revises: 469b0bed9d77
Create Date: 2026-09-27

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "4c8e7a91d2f0"
down_revision: Union[str, Sequence[str], None] = "469b0bed9d77"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Supprime la contrainte avant de retirer la colonne.
    op.drop_constraint(
        "recruteur_id_entreprise_fkey",
        "recruteur",
        type_="foreignkey",
    )

    # Supprime définitivement les données entreprise associées
    # aux recruteurs existants.
    op.drop_column(
        "recruteur",
        "id_entreprise",
    )

    # Supprime définitivement la table et toutes ses données.
    op.drop_table("entreprise")


def downgrade() -> None:
    # Cette fonctionnalité est volontairement retirée du produit.
    # Pas de restauration automatique des données supprimées.
    raise NotImplementedError(
        "La fonctionnalité entreprise a été supprimée du produit."
    )