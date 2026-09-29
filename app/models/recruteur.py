import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Recruteur(Base):
    __tablename__ = "recruteur"

    id_recruteur: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    id_utilisateur: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateur.id_utilisateur"),
        unique=True,
        nullable=False,
    )

    persona: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Relations
    utilisateur: Mapped["Utilisateur"] = relationship(
        back_populates="recruteur"
    )

    offres: Mapped[list["Offre"]] = relationship(
        back_populates="recruteur"
    )
