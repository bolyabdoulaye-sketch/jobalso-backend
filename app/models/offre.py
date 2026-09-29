import uuid
from datetime import datetime, date

from sqlalchemy import String, Float, Boolean, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

from app.db.base import Base


class Offre(Base):
    __tablename__ = "offre"

    id_offre: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_recruteur: Mapped[uuid.UUID] = mapped_column(ForeignKey("recruteur.id_recruteur"), nullable=False)

    titre_offre: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    type_contrat: Mapped[str | None] = mapped_column(String(50), nullable=True)
    revenu: Mapped[float | None] = mapped_column(Float, nullable=True)

    offre_vector: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)

    entretien: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    date_debut: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_fin: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    resume_offre: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Lien de candidature publique unique et non devinable (JA-026)
    lien_token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    date_publication: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    date_modification: Mapped[datetime | None] = mapped_column(DateTime, onupdate=datetime.utcnow, nullable=True)

    # Relations
    recruteur: Mapped["Recruteur"] = relationship(back_populates="offres")
    resultats: Mapped[list["Resultat"]] = relationship(back_populates="offre")
    criteres: Mapped[list["CritereOffre"]] = relationship(
        back_populates="offre", cascade="all, delete-orphan"
    )
