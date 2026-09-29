"""supprimer notifications email

Revision ID: 056123b9049b
Revises: 5fb200140435
Create Date: 2026-09-28
"""

from alembic import op


revision = "056123b9049b"
down_revision = "5fb200140435"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("utilisateur", "notifications_email")


def downgrade() -> None:
    raise NotImplementedError(
        "La restauration de notifications_email n'est pas supportee."
    )