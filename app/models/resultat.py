import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.dates import utcnow
from app.db.base import Base


class Resultat(Base):
    __tablename__ = "resultat"
    # Une seule candidature par CV et par offre, garanti par la base.
    __table_args__ = (UniqueConstraint("id_offre", "id_cv", name="uq_resultat_offre_cv"),)

    id_resultat: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_offre: Mapped[uuid.UUID] = mapped_column(ForeignKey("offre.id_offre", ondelete="CASCADE"), nullable=False, index=True)
    id_cv: Mapped[uuid.UUID] = mapped_column(ForeignKey("cv.id_cv", ondelete="CASCADE"), nullable=False, index=True)

    score_sim: Mapped[float] = mapped_column(Float, nullable=False)
    statut_candidature: Mapped[str | None] = mapped_column(String(50), nullable=True)

    date_modification: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=True)

    # Relations
    offre: Mapped["Offre"] = relationship(back_populates="resultats")
    cv: Mapped["CV"] = relationship(back_populates="resultats")
