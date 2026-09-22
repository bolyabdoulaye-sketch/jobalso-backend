import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Resultat(Base):
    __tablename__ = "resultat"

    id_resultat: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_offre: Mapped[uuid.UUID] = mapped_column(ForeignKey("offre.id_offre"), nullable=False)
    id_cv: Mapped[uuid.UUID] = mapped_column(ForeignKey("cv.id_cv"), nullable=False)

    score_sim: Mapped[float] = mapped_column(Float, nullable=False)
    statut_candidature: Mapped[str | None] = mapped_column(String(50), nullable=True)

    date_modification: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    # Relations
    offre: Mapped["Offre"] = relationship(back_populates="resultats")
    cv: Mapped["CV"] = relationship(back_populates="resultats")