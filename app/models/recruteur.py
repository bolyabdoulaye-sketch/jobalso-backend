import uuid
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Recruteur(Base):
    __tablename__ = "recruteur"

    id_recruteur: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_utilisateur: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateur.id_utilisateur"), unique=True, nullable=False)
    id_entreprise: Mapped[uuid.UUID] = mapped_column(ForeignKey("entreprise.id_entreprise"), nullable=False)

    # Relations
    utilisateur: Mapped["Utilisateur"] = relationship(back_populates="recruteur")
    entreprise: Mapped["Entreprise"] = relationship(back_populates="recruteurs")
    offres: Mapped[list["Offre"]] = relationship(back_populates="recruteur")