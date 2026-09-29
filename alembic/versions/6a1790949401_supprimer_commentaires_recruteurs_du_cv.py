"""supprimer commentaires recruteurs du cv

Revision ID: 6a1790949401
Revises: 056123b9049b
"""

from alembic import op


revision = "6a1790949401"
down_revision = "056123b9049b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("cv", "commentaires_recruteurs")


def downgrade() -> None:
    raise NotImplementedError(
        "La restauration de commentaires_recruteurs n'est pas supportee."
    )