import enum
import uuid

from sqlalchemy import String, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class NiveauCritere(str, enum.Enum):
    OBLIGATOIRE = "OBLIGATOIRE"
    IMPORTANT = "IMPORTANT"
    SOUHAITABLE = "SOUHAITABLE"


class CritereOffre(Base):
    __tablename__ = "critere_offre"

    id_critere: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_offre: Mapped[uuid.UUID] = mapped_column(ForeignKey("offre.id_offre"), nullable=False, index=True)
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    niveau: Mapped[NiveauCritere] = mapped_column(
        Enum(NiveauCritere), nullable=False, default=NiveauCritere.IMPORTANT
    )

    # Relations
    offre: Mapped["Offre"] = relationship(back_populates="criteres")
