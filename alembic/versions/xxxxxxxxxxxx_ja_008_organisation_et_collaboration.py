"""JA-008 organisation et collaboration

Revision ID: xxxxxxxxxxxx
Revises: 6a1790949401
"""

import uuid

from alembic import op
import sqlalchemy as sa


revision = "xxxxxxxxxxxx"
down_revision = "6a1790949401"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # 1. ORGANISATION
    # ============================================================

    op.create_table(
        "organisation",
        sa.Column(
            "id_organisation",
            sa.UUID(),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "nom",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "date_creation",
            sa.DateTime(),
            nullable=False,
        ),
        sa.Column(
            "date_modification",
            sa.DateTime(),
            nullable=True,
        ),
    )

    # ============================================================
    # 2. MEMBRES ORGANISATION
    # ============================================================

    role_organisation_enum = sa.Enum(
        "ADMIN",
        "MEMBRE",
        name="roleorganisation",
    )
    
    op.create_table(
        "membre_organisation",
        sa.Column(
            "id_organisation",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "id_utilisateur",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "role",
            role_organisation_enum,
            nullable=False,
        ),
        sa.Column(
            "date_ajout",
            sa.DateTime(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["id_organisation"],
            ["organisation.id_organisation"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["id_utilisateur"],
            ["utilisateur.id_utilisateur"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id_organisation",
            "id_utilisateur",
        ),
    )

    # ============================================================
    # 3. INVITATIONS ORGANISATION
    # ============================================================

    role_invitation_enum = sa.Enum(
        "ADMIN",
        "MEMBRE",
        name="roleinvitationorganisation",
    )
    
    op.create_table(
        "invitation_organisation",
        sa.Column(
            "id_invitation",
            sa.UUID(),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "id_organisation",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "email",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "role",
            role_invitation_enum,
            nullable=False,
        ),
        sa.Column(
            "token",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "date_creation",
            sa.DateTime(),
            nullable=False,
        ),
        sa.Column(
            "date_expiration",
            sa.DateTime(),
            nullable=True,
        ),
        sa.Column(
            "date_utilisation",
            sa.DateTime(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["id_organisation"],
            ["organisation.id_organisation"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("token"),
    )

    op.create_index(
        "ix_invitation_organisation_id_organisation",
        "invitation_organisation",
        ["id_organisation"],
    )

    op.create_index(
        "ix_invitation_organisation_email",
        "invitation_organisation",
        ["email"],
    )

    op.create_index(
        "ix_invitation_organisation_token",
        "invitation_organisation",
        ["token"],
    )

    # ============================================================
    # 4. AJOUT PROGRESSIF DE id_organisation SUR offre
    # ============================================================

    op.add_column(
        "offre",
        sa.Column(
            "id_organisation",
            sa.UUID(),
            nullable=True,
        ),
    )

    # ============================================================
    # 5. REPRISE DES DONNÉES EXISTANTES
    #
    # Pour chaque recruteur existant :
    #   - création d'une organisation
    #   - recruteur => ADMIN
    #   - offres du recruteur => organisation
    # ============================================================

    connection = op.get_bind()

    recruteurs = connection.execute(
        sa.text(
            """
            SELECT
                r.id_recruteur,
                r.id_utilisateur
            FROM recruteur r
            """
        )
    ).fetchall()

    now = sa.func.now()

    for recruteur in recruteurs:
        id_organisation = uuid.uuid4()

        connection.execute(
            sa.text(
                """
                INSERT INTO organisation (
                    id_organisation,
                    nom,
                    date_creation
                )
                VALUES (
                    :id_organisation,
                    :nom,
                    CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "id_organisation": id_organisation,
                "nom": f"Organisation du recruteur {recruteur.id_recruteur}",
            },
        )

        connection.execute(
            sa.text(
                """
                INSERT INTO membre_organisation (
                    id_organisation,
                    id_utilisateur,
                    role,
                    date_ajout
                )
                VALUES (
                    :id_organisation,
                    :id_utilisateur,
                    'ADMIN',
                    CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "id_organisation": id_organisation,
                "id_utilisateur": recruteur.id_utilisateur,
            },
        )

        connection.execute(
            sa.text(
                """
                UPDATE offre
                SET id_organisation = :id_organisation
                WHERE id_recruteur = :id_recruteur
                """
            ),
            {
                "id_organisation": id_organisation,
                "id_recruteur": recruteur.id_recruteur,
            },
        )

    # ============================================================
    # 6. SÉCURITÉ : aucune offre orpheline
    # ============================================================

    offres_orphelines = connection.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM offre
            WHERE id_organisation IS NULL
            """
        )
    ).scalar_one()

    if offres_orphelines != 0:
        raise RuntimeError(
            f"{offres_orphelines} offre(s) n'ont pas pu être rattachées "
            "à une organisation."
        )

    # ============================================================
    # 7. FK + NOT NULL
    # ============================================================

    op.create_foreign_key(
        "fk_offre_organisation",
        "offre",
        "organisation",
        ["id_organisation"],
        ["id_organisation"],
    )

    op.alter_column(
        "offre",
        "id_organisation",
        existing_type=sa.UUID(),
        nullable=False,
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Cette migration contient une reprise de données "
        "organisationnelles et n'est pas réversible automatiquement."
    )