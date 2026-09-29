"""cascades de suppression, sessions de connexion et unicité des candidatures

- ON DELETE CASCADE : critères, candidatures et historique suivent la
  suppression d'une offre ou d'un CV (droit à l'effacement, Loi 25) ;
- une seule candidature par CV et par offre ;
- table session_utilisateur pour les jetons de rafraîchissement.

Revision ID: f2ec64db6b86
Revises: xxxxxxxxxxxx
"""

from alembic import op
import sqlalchemy as sa


revision = "f2ec64db6b86"
down_revision = "xxxxxxxxxxxx"
branch_labels = None
depends_on = None


# (table, contrainte, colonne, table cible, colonne cible)
CLES_ETRANGERES = [
    ("critere_offre", "critere_offre_id_offre_fkey", "id_offre", "offre", "id_offre"),
    ("resultat", "resultat_id_offre_fkey", "id_offre", "offre", "id_offre"),
    ("resultat", "resultat_id_cv_fkey", "id_cv", "cv", "id_cv"),
    (
        "historique_statut_candidature",
        "historique_statut_candidature_id_resultat_fkey",
        "id_resultat",
        "resultat",
        "id_resultat",
    ),
]


def _recreer_cles(ondelete: str | None) -> None:
    for table, nom, colonne, cible, colonne_cible in CLES_ETRANGERES:
        op.drop_constraint(nom, table, type_="foreignkey")
        op.create_foreign_key(nom, table, cible, [colonne], [colonne_cible], ondelete=ondelete)


def upgrade() -> None:
    _recreer_cles("CASCADE")

    doublons = op.get_bind().execute(
        sa.text(
            "SELECT COUNT(*) FROM ("
            " SELECT id_offre, id_cv FROM resultat"
            " GROUP BY id_offre, id_cv HAVING COUNT(*) > 1"
            ") d"
        )
    ).scalar_one()
    if doublons:
        raise RuntimeError(
            f"{doublons} candidature(s) en double (meme CV, meme offre) : "
            "a dedoublonner a la main avant cette migration."
        )

    op.create_unique_constraint("uq_resultat_offre_cv", "resultat", ["id_offre", "id_cv"])
    op.create_index("ix_resultat_id_offre", "resultat", ["id_offre"])
    op.create_index("ix_resultat_id_cv", "resultat", ["id_cv"])

    op.create_table(
        "session_utilisateur",
        sa.Column("id_session", sa.UUID(), nullable=False),
        sa.Column("id_utilisateur", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("date_creation", sa.DateTime(), nullable=False),
        sa.Column("date_expiration", sa.DateTime(), nullable=False),
        sa.Column("date_revocation", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["id_utilisateur"], ["utilisateur.id_utilisateur"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id_session"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_session_utilisateur_id_utilisateur", "session_utilisateur", ["id_utilisateur"]
    )


def downgrade() -> None:
    op.drop_index("ix_session_utilisateur_id_utilisateur", table_name="session_utilisateur")
    op.drop_table("session_utilisateur")
    op.drop_index("ix_resultat_id_cv", table_name="resultat")
    op.drop_index("ix_resultat_id_offre", table_name="resultat")
    op.drop_constraint("uq_resultat_offre_cv", "resultat", type_="unique")
    _recreer_cles(None)
