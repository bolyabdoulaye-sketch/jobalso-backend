"""add profile and company uniqueness constraints

Revision ID: b6a4d9f2c810
Revises: 963ceb737713
Create Date: 2026-09-24
"""

from typing import Sequence, Union

from alembic import op


revision: str = "b6a4d9f2c810"
down_revision: Union[str, None] = "963ceb737713"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_administrateur_id_utilisateur", "administrateur", ["id_utilisateur"]
    )
    op.create_unique_constraint(
        "uq_candidat_id_utilisateur", "candidat", ["id_utilisateur"]
    )
    op.create_unique_constraint(
        "uq_recruteur_id_utilisateur", "recruteur", ["id_utilisateur"]
    )
    op.create_unique_constraint(
        "uq_entreprise_nom_pays_localisation",
        "entreprise",
        ["nom_entreprise", "pays", "localisation_entreprise"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_entreprise_nom_pays_localisation", "entreprise", type_="unique")
    op.drop_constraint("uq_recruteur_id_utilisateur", "recruteur", type_="unique")
    op.drop_constraint("uq_candidat_id_utilisateur", "candidat", type_="unique")
    op.drop_constraint("uq_administrateur_id_utilisateur", "administrateur", type_="unique")
