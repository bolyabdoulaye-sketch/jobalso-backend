"""add candidature table

Revision ID: 825fe45a3ac7
Revises: c7f8a1b2d3e4
Create Date: 2026-09-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '825fe45a3ac7'
down_revision: Union[str, None] = 'c7f8a1b2d3e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Define the enum type with create_type=False to avoid recreating it
etape_enum = postgresql.ENUM('candidature', 'shortlist', 'entrevue', 'decision',
                           name='minietapecandidatureenum',
                           create_type=False)


def upgrade() -> None:
    # Create the enum type if it doesn't exist (safe check)
    etape_enum.create(op.get_bind(), checkfirst=True)
    
    # Create the candidature table
    op.create_table('candidature',
        sa.Column('id_candidature', sa.UUID(), nullable=False),
        sa.Column('id_offre', sa.UUID(), nullable=False),
        sa.Column('id_candidat', sa.UUID(), nullable=False),
        sa.Column('id_cv', sa.UUID(), nullable=True),
        sa.Column('source_candidature', sa.String(length=30), nullable=False, server_default='lien_public'),
        sa.Column('etape_courante', etape_enum, nullable=False, server_default='candidature'),
        sa.Column('date_candidature', sa.DateTime(), nullable=False),
        sa.Column('date_modification', sa.DateTime(), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['id_cv'], ['cv.id_cv'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['id_candidat'], ['candidat.id_candidat'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['id_offre'], ['offre.id_offre'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id_candidature')
    )


def downgrade() -> None:
    # Drop the candidature table
    op.drop_table('candidature')
    
    # Drop the enum type
    etape_enum.drop(op.get_bind(), checkfirst=True)
